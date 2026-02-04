"""Kafka pub/sub backend implementation.

This module provides a Kafka-based implementation of the PubSubBackend interface
using the confluent-kafka library. It supports publish/subscribe messaging patterns
with Apache Kafka brokers, including advanced features like SASL authentication
and TLS/SSL encryption.

The KafkaPubSub class handles both producer and consumer operations, managing
connections to Kafka brokers and providing a simple interface for publishing
and subscribing to topics.

Example:
    Basic usage with local Kafka::

        from msight_core.pubsub import KafkaPubSub
        from msight_core.pubsub.utils import get_kafka_config

        config = get_kafka_config(group_id="my_consumer_group")
        kafka = KafkaPubSub(config)

        # Subscribe to a topic
        kafka.subscribe(topic)

        # Listen for messages
        for message in kafka.listen():
            print(f"Received: {message}")

        # Publish a message
        kafka.publish(topic, b"Hello, Kafka!")

    With SASL authentication and TLS::

        import os
        os.environ["MSIGHT_KAFKA_SERVERS"] = "['broker1:9093', 'broker2:9093']"
        os.environ["MSIGHT_KAFKA_SASL_MECHANISM"] = "SCRAM-SHA-256"
        os.environ["MSIGHT_KAFKA_SASL_USERNAME"] = "user"
        os.environ["MSIGHT_KAFKA_SASL_PASSWORD"] = "pass"
        os.environ["MSIGHT_KAFKA_USE_TLS"] = "true"

        config = get_kafka_config(group_id="my_group")
        kafka = KafkaPubSub(config)

See Also:
    - :func:`msight_core.pubsub.utils.get_kafka_config`: Configuration helper
    - :class:`msight_core.pubsub.base.PubSubBackend`: Base interface
"""

from confluent_kafka import Producer, Consumer
from .base import PubSubBackend


class KafkaPubSub(PubSubBackend):
    """Kafka pub/sub backend using confluent-kafka.

    This class implements the PubSubBackend interface for Apache Kafka,
    providing producer and consumer functionality with support for consumer
    groups, SASL authentication, and TLS encryption.

    The producer is created immediately upon initialization, while the consumer
    is lazily created when :meth:`subscribe` is called.

    Attributes:
        bootstrap_servers (list): List of Kafka broker addresses.
        group_id (str): Consumer group identifier for coordinated consumption.
        producer (Producer): Confluent Kafka producer instance.
        consumer (Consumer or None): Confluent Kafka consumer instance (created on subscribe).
        topic (Topic or None): Currently subscribed topic object.

    Args:
        config (dict): Configuration dictionary containing Kafka settings.
            Must include:

            - ``servers`` (list): List of broker addresses (e.g., ``['localhost:9092']``)
            - ``group_id`` (str): Consumer group ID

            Optional keys (for authentication and encryption):

            - ``sasl_mechanism`` (str): SASL mechanism (PLAIN, SCRAM-SHA-256, etc.)
            - ``sasl_plain_username`` (str): Username for SASL authentication
            - ``sasl_plain_password`` (str): Password for SASL authentication
            - ``security_protocol`` (str): Security protocol (PLAINTEXT, SASL_SSL, etc.)
            - ``ssl_cafile`` (str): Path to CA certificate file
            - ``ssl_certfile`` (str): Path to client certificate file
            - ``ssl_keyfile`` (str): Path to client key file

    Raises:
        ValueError: If ``group_id`` is not provided in the configuration.

    Example:
        Initialize with minimal configuration::

            config = {
                'servers': ['localhost:9092'],
                'group_id': 'my_app_consumers'
            }
            kafka = KafkaPubSub(config)

        Initialize with SASL and TLS::

            config = {
                'servers': ['broker:9093'],
                'group_id': 'secure_group',
                'sasl_mechanism': 'SCRAM-SHA-256',
                'sasl_plain_username': 'user',
                'sasl_plain_password': 'secret',
                'security_protocol': 'SASL_SSL',
                'ssl_cafile': '/path/to/ca.pem'
            }
            kafka = KafkaPubSub(config)
    """

    def __init__(self, config):
        """Initialize Kafka pub/sub backend.

        Args:
            config (dict): Kafka configuration dictionary.

        Raises:
            ValueError: If ``group_id`` is missing from config.
        """
        self.config = config  # Store full config for reuse
        self.bootstrap_servers = config.get('servers', ['localhost:9092'])
        if 'group_id' not in config:
            raise ValueError("Kafka configuration must include 'group_id'")
        self.group_id = config['group_id']
        
        # Build producer configuration
        producer_config = {
            'bootstrap.servers': ','.join(self.bootstrap_servers)
        }
        
        # Add security configurations if present
        if 'security_protocol' in config:
            producer_config['security.protocol'] = config['security_protocol']
        if 'sasl_mechanism' in config:
            producer_config['sasl.mechanism'] = config['sasl_mechanism']
        if 'sasl_plain_username' in config:
            producer_config['sasl.username'] = config['sasl_plain_username']
        if 'sasl_plain_password' in config:
            producer_config['sasl.password'] = config['sasl_plain_password']
        if 'ssl_cafile' in config:
            producer_config['ssl.ca.location'] = config['ssl_cafile']
        if 'ssl_certfile' in config:
            producer_config['ssl.certificate.location'] = config['ssl_certfile']
        if 'ssl_keyfile' in config:
            producer_config['ssl.key.location'] = config['ssl_keyfile']
        
        self.producer = Producer(producer_config)
        self.consumer = None
        self.topic = None

    def subscribe(self, topic):
        """Subscribe to a Kafka topic for consuming messages.

        Creates a Kafka consumer configured with the provided topic and
        consumer group settings. The consumer will start reading from the
        earliest available offset for new consumer groups.

        Note:
            This method must be called before :meth:`listen`.

        Args:
            topic (Topic): Topic object containing the topic name and configuration.

        Example:
            Subscribe to a topic::

                from msight_core.topics import get_topic
                topic = get_topic(redis_client, "sensor_data")
                kafka.subscribe(topic)
        """
        self.topic = topic

        # Build consumer configuration
        consumer_config = {
            'bootstrap.servers': ','.join(self.bootstrap_servers),
            'group.id': self.group_id,
            'auto.offset.reset': 'earliest'  # or 'latest' if preferred
        }
        
        # Add security configurations from stored config
        if 'security_protocol' in self.config:
            consumer_config['security.protocol'] = self.config['security_protocol']
        if 'sasl_mechanism' in self.config:
            consumer_config['sasl.mechanism'] = self.config['sasl_mechanism']
        if 'sasl_plain_username' in self.config:
            consumer_config['sasl.username'] = self.config['sasl_plain_username']
        if 'sasl_plain_password' in self.config:
            consumer_config['sasl.password'] = self.config['sasl_plain_password']
        if 'ssl_cafile' in self.config:
            consumer_config['ssl.ca.location'] = self.config['ssl_cafile']
        if 'ssl_certfile' in self.config:
            consumer_config['ssl.certificate.location'] = self.config['ssl_certfile']
        if 'ssl_keyfile' in self.config:
            consumer_config['ssl.key.location'] = self.config['ssl_keyfile']
        
        self.consumer = Consumer(consumer_config)
        self.consumer.subscribe([self.topic.name])

    def publish(self, topic, serialized_data):
        """Publish a message to a Kafka topic.

        Sends serialized data to the specified topic and flushes to ensure
        delivery. This is a synchronous operation that blocks until the
        message is acknowledged by the broker.

        Args:
            topic (Topic): Topic object containing the topic name.
            serialized_data (bytes): Serialized message payload to publish.

        Example:
            Publish a message::

                from msight_core.data import SensorData
                data = SensorData(sensor_name="camera1")
                kafka.publish(topic, data.serialize())
        """
        self.producer.produce(topic.name, value=serialized_data)
        self.producer.flush()  # optional but ensures the message is delivered

    def listen(self):
        """Listen for messages from the subscribed topic.

        Yields messages as they arrive from the Kafka topic. This is a blocking
        generator that continuously polls the Kafka consumer for new messages.

        Note:
            :meth:`subscribe` must be called before using this method.

        Yields:
            bytes (bytes): Serialized message data received from the topic.

        Raises:
            RuntimeError: If called before :meth:`subscribe` or if a Kafka error occurs.

        Example:
            Process messages in a loop::

                kafka.subscribe(topic)
                for message_data in kafka.listen():
                    data = SensorData.deserialize(message_data)
                    print(f"Received from {data.sensor_name}")

            With error handling::

                try:
                    for message_data in kafka.listen():
                        process_message(message_data)
                except RuntimeError as e:
                    logger.error(f"Kafka error: {e}")
        """
        if not self.consumer:
            raise RuntimeError("Must call subscribe(topic) before listen()")

        while True:
            msg = self.consumer.poll(1.0)  # timeout in seconds
            if msg is None:
                continue
            if msg.error():
                raise RuntimeError(f"Kafka error: {msg.error()}")
            yield msg.value()

