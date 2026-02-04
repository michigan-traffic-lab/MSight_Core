"""Redis pub/sub backend implementation.

This module provides a Redis-based implementation of the PubSubBackend interface
using the redis-py library. It leverages Redis's built-in pub/sub messaging
capabilities for lightweight, fast message distribution.

Redis pub/sub is ideal for scenarios requiring simple message broadcasting with
low latency. Note that Redis pub/sub is fire-and-forget - messages are only
delivered to currently connected subscribers and are not persisted.

The RedisPubSub class wraps Redis's native pub/sub functionality, providing a
simple interface consistent with other MSight messaging backends.

Example:
    Basic usage with local Redis::

        from msight_core.pubsub import RedisPubSub
        from msight_core.utils import get_redis_client

        redis_client = get_redis_client()
        redis_pubsub = RedisPubSub(redis_client)

        # Subscribe to a topic
        redis_pubsub.subscribe(topic)

        # Listen for messages
        for message in redis_pubsub.listen():
            print(f"Received: {message}")

        # Publish a message
        redis_pubsub.publish(topic, b"Hello, Redis!")

    With Redis authentication and TLS::

        import os
        os.environ["MSIGHT_REDIS_MESSAGE_BROKER_HOST"] = "redis.example.com"
        os.environ["MSIGHT_REDIS_MESSAGE_BROKER_PORT"] = "6380"
        os.environ["MSIGHT_REDIS_MESSAGE_BROKER_USERNAME"] = "user"
        os.environ["MSIGHT_REDIS_MESSAGE_BROKER_PASSWORD"] = "pass"
        os.environ["MSIGHT_REDIS_MESSAGE_BROKER_USE_TLS"] = "true"

        redis_client = get_redis_client()
        redis_pubsub = RedisPubSub(redis_client)

Important:
    Redis pub/sub does not persist messages. If a subscriber is disconnected
    when a message is published, that message is lost. For reliable message
    delivery with persistence, consider using Kafka or NATS JetStream instead.

See Also:
    - :func:`msight_core.utils.get_redis_client`: Redis client factory
    - :class:`msight_core.pubsub.base.PubSubBackend`: Base interface
"""

from .base import PubSubBackend


class RedisPubSub(PubSubBackend):
    """Redis pub/sub backend using redis-py.

    This class implements the PubSubBackend interface using Redis's native
    publish/subscribe functionality. It provides a simple, low-latency
    messaging solution suitable for real-time data distribution where message
    persistence is not required.

    Redis pub/sub operates in a broadcast mode where all subscribers to a
    channel receive every message. There is no consumer group concept or
    message replay capability.

    Attributes:
        r (redis.Redis): Redis client instance for publishing.
        pubsub (redis.client.PubSub): Redis pub/sub object for subscribing.
        subscribed (bool): Flag indicating whether a subscription is active.

    Args:
        redis_client (redis.Redis): Connected Redis client instance.
            This client should be obtained from :func:`get_redis_client`
            which handles connection configuration, authentication, and TLS.

    Example:
        Initialize with Redis client::

            from msight_core.utils import get_redis_client
            redis_client = get_redis_client()
            redis_pubsub = RedisPubSub(redis_client)

        With cluster mode::

            import os
            os.environ["MSIGHT_REDIS_MESSAGE_BROKER_USE_CLUSTER"] = "true"
            os.environ["MSIGHT_REDIS_MESSAGE_BROKER_CLUSTER_NODES"] = "['node1:6379', 'node2:6379']"

            redis_client = get_redis_client()  # Returns RedisCluster
            redis_pubsub = RedisPubSub(redis_client)

    Note:
        The Redis client is used for both publishing (via ``self.r``) and
        subscribing (via ``self.pubsub``). The pub/sub object is created
        immediately but subscription doesn't occur until :meth:`subscribe`
        is called.
    """

    def __init__(self, redis_client):
        """Initialize Redis pub/sub backend.

        Creates a pub/sub object from the provided Redis client. The client
        should already be connected and configured with any necessary
        authentication or TLS settings.

        Args:
            redis_client (redis.Redis or redis.RedisCluster): Connected Redis
                client instance.
        """
        self.r = redis_client
        self.pubsub = self.r.pubsub()
        self.subscribed = False

    def subscribe(self, topic):
        """Subscribe to a Redis channel for consuming messages.

        Subscribes to the specified topic's channel in Redis. All messages
        published to this channel will be received by this subscriber.

        Unlike Kafka or NATS with queue groups, Redis pub/sub delivers every
        message to every subscriber. Multiple subscribers will each receive
        a copy of every message.

        Note:
            This method must be called before :meth:`listen`.

        Args:
            topic (Topic): Topic object containing the channel name and configuration.

        Example:
            Subscribe to a topic::

                from msight_core.topics import get_topic
                topic = get_topic(redis_client, "sensor_data")
                redis_pubsub.subscribe(topic)
        """
        self.pubsub.subscribe(topic.name)
        self.subscribed = True

    def publish(self, topic, serialized_data):
        """Publish a message to a Redis channel.

        Sends serialized data to the specified channel. The message is
        immediately delivered to all currently connected subscribers.

        Redis pub/sub is fire-and-forget with no acknowledgments. If no
        subscribers are connected, the message is silently discarded. If
        a subscriber disconnects before receiving the message, it is lost.

        Args:
            topic (Topic): Topic object containing the channel name.
            serialized_data (bytes): Serialized message payload to publish.

        Returns:
            num (int): Number of subscribers that received the message.

        Example:
            Publish a message::

                from msight_core.data import SensorData
                data = SensorData(sensor_name="camera1")
                num_receivers = redis_pubsub.publish(topic, data.serialize())
                print(f"Message delivered to {num_receivers} subscribers")
        """
        self.r.publish(topic.name, serialized_data)

    def listen(self):
        """Listen for messages from the subscribed channel.

        Yields messages as they arrive from the Redis channel. This is a
        blocking generator that continuously listens for new messages.

        The method filters out Redis pub/sub control messages (like subscribe
        confirmations) and only yields actual data messages.

        Note:
            :meth:`subscribe` must be called before using this method.

        Yields:
            serialized_message (bytes): Serialized message data received from the channel.

        Raises:
            RuntimeError: If called before :meth:`subscribe`.

        Example:
            Process messages in a loop::

                redis_pubsub.subscribe(topic)
                for message_data in redis_pubsub.listen():
                    data = SensorData.deserialize(message_data)
                    print(f"Received from {data.sensor_name}")

            With timeout handling::

                redis_pubsub.subscribe(topic)
                import time
                last_message = time.time()

                for message_data in redis_pubsub.listen():
                    process_message(message_data)
                    last_message = time.time()

                    if time.time() - last_message > 30:
                        logger.warning("No messages for 30 seconds")

        Warning:
            This method blocks indefinitely. Ensure proper signal handling
            or timeouts are in place for graceful shutdown.
        """
        if not self.subscribed:
            raise RuntimeError("Must call subscribe(topic) before listen()")
        for msg in self.pubsub.listen():
            if msg['type'] == 'message':
                yield msg['data']

