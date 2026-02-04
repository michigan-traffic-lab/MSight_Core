"""Pub/sub backend base interface.

This module defines the abstract base class for all MSight pub/sub backend
implementations. It provides a unified interface for publish/subscribe messaging
across different message brokers (Redis, NATS, Kafka, etc.).

The PubSubBackend interface enables pluggable messaging backends, allowing
applications to switch between different message brokers without changing
application code. This abstraction supports various use cases from simple
in-process messaging with Redis to distributed, persistent messaging with Kafka.

Example:
    Implementing a custom pub/sub backend::

        from msight_core.pubsub.base import PubSubBackend

        class MyCustomPubSub(PubSubBackend):
            def __init__(self, config):
                self.config = config
                # Initialize your message broker connection

            def subscribe(self, topic):
                # Implement subscription logic
                pass

            def publish(self, topic, serialized_data):
                # Implement publishing logic
                pass

            def listen(self):
                # Implement message listening logic
                while True:
                    message = self._get_next_message()
                    yield message

    Using different backends interchangeably::

        # Choose backend via environment variable
        import os
        from msight_core.utils import get_redis_client
        from msight_core.pubsub import RedisPubSub, NATSPubSub, KafkaPubSub

        backend_type = os.getenv("MSIGHT_PUBSUB_BACKEND", "redis")

        if backend_type == "redis":
            pubsub = RedisPubSub(get_redis_client())
        elif backend_type == "nats":
            pubsub = NATSPubSub(get_nats_config(group_id="my_group"))
        elif backend_type == "kafka":
            pubsub = KafkaPubSub(get_kafka_config(group_id="my_group"))

        # Same interface regardless of backend
        pubsub.subscribe(topic)
        for message in pubsub.listen():
            process(message)

See Also:
    - :class:`msight_core.pubsub.RedisPubSub`: Redis implementation
    - :class:`msight_core.pubsub.NATSPubSub`: NATS implementation
    - :class:`msight_core.pubsub.KafkaPubSub`: Kafka implementation
"""

from abc import ABC, abstractmethod
from msight_core.topics import Topic


class PubSubBackend(ABC):
    """Abstract base class for pub/sub messaging backends.

    This class defines the interface that all MSight pub/sub backends must
    implement. It provides three core operations: subscribing to topics,
    publishing messages, and listening for incoming messages.

    Implementations must handle the specifics of connecting to their respective
    message brokers, managing subscriptions, and converting between the broker's
    native message format and MSight's serialized data format.

    The interface is designed to be simple and consistent across different
    messaging systems, abstracting away broker-specific details like consumer
    groups, acknowledgments, and connection management.

    Note:
        All methods must be implemented by subclasses. This is an abstract
        base class and cannot be instantiated directly.

    Example:
        All implementations follow the same usage pattern::

            # Initialize with backend-specific config
            pubsub = SomePubSubBackend(config)

            # Subscribe to a topic
            pubsub.subscribe(topic)

            # Publish messages
            pubsub.publish(topic, serialized_data)

            # Listen for messages
            for message in pubsub.listen():
                process(message)
    """

    @abstractmethod
    def subscribe(self, topic: Topic):
        """Subscribe to a topic for receiving messages.

        Establishes a subscription to the specified topic. After subscribing,
        messages published to this topic can be retrieved via the :meth:`listen`
        method.

        The behavior may vary by implementation:
        
        - **Redis**: Subscribes to a channel; all subscribers receive all messages
        - **NATS**: Can use queue groups for load-balanced distribution
        - **Kafka**: Uses consumer groups for distributed consumption with offset tracking

        Note:
            This method must be called before :meth:`listen`. Some implementations
            may support multiple simultaneous subscriptions.

        Args:
            topic: Topic object containing the topic/channel name and metadata.
                Typically obtained from :func:`msight_core.topics.get_topic`.

        Example:
            Subscribe to a sensor data topic::

                from msight_core.topics import get_topic

                topic = get_topic(redis_client, "sensor_data")
                pubsub.subscribe(topic)

        See Also:
            :meth:`listen`: Retrieve messages from subscribed topics
        """
        pass

    @abstractmethod
    def publish(self, topic: Topic, serialized_data: bytes):
        """Publish a message to a topic.

        Sends serialized data to the specified topic. The message will be
        delivered according to the backend's semantics:

        - **Redis**: Immediate delivery to all connected subscribers (fire-and-forget)
        - **NATS**: Immediate delivery with optional persistence in JetStream
        - **Kafka**: Persistent storage with guaranteed delivery to consumer groups

        The method may block until the message is sent, acknowledged, or queued,
        depending on the implementation.

        Args:
            topic (Topic): Topic object containing the destination topic/channel name.
            serialized_data (bytes): Pre-serialized message payload. Typically
                produced by calling ``.serialize()`` on a :class:`Data` instance.

        Example:
            Publish sensor data::

                from msight_core.data import SensorData

                data = SensorData(sensor_name="camera1", frame_id=12345)
                serialized = data.serialize()
                pubsub.publish(topic, serialized)

            Publish with error handling::

                try:
                    pubsub.publish(topic, data.serialize())
                except Exception as e:
                    logger.error(f"Failed to publish: {e}")

        See Also:
            :meth:`subscribe`: Receive messages from topics
        """
        pass

    @abstractmethod
    def listen(self):
        """Listen for messages from subscribed topics.

        Returns a generator that yields messages as they arrive from subscribed
        topics. This is a blocking operation that continuously waits for new
        messages.

        The generator runs indefinitely until the connection is closed or an
        error occurs. Implementations should filter out any broker-specific
        control messages and only yield actual data messages.

        Note:
            :meth:`subscribe` must be called before using this method, otherwise
            implementations should raise a ``RuntimeError``.

        Yields:
            bytes (bytes): Serialized message data. Deserialize using the appropriate
                :class:`Data` subclass's ``.deserialize()`` method.

        Raises:
            RuntimeError: If called before subscribing to a topic.
            Exception: Implementation-specific errors (connection loss, etc.)

        Example:
            Basic message processing loop::

                pubsub.subscribe(topic)

                for message_data in pubsub.listen():
                    data = SensorData.deserialize(message_data)
                    print(f"Received from {data.sensor_name}: {data.frame_id}")

            With error handling and graceful shutdown::

                pubsub.subscribe(topic)

                try:
                    for message_data in pubsub.listen():
                        try:
                            data = Data.deserialize(message_data)
                            process_data(data)
                        except Exception as e:
                            logger.error(f"Failed to process message: {e}")
                except KeyboardInterrupt:
                    logger.info("Shutting down...")
                except Exception as e:
                    logger.error(f"Connection error: {e}")

            Processing multiple message types::

                for message_data in pubsub.listen():
                    data = Data.deserialize(message_data)
                    
                    if isinstance(data, ImageData):
                        process_image(data)
                    elif isinstance(data, PointCloudData):
                        process_pointcloud(data)

        Warning:
            This method blocks indefinitely. Ensure proper signal handling
            or timeouts are implemented for graceful application shutdown.

        See Also:
            :meth:`subscribe`: Subscribe to topics before listening
            :meth:`publish`: Send messages to topics
        """
        pass


