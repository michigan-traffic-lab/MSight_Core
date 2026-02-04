"""NATS pub/sub backend implementation.

This module provides a NATS-based implementation of the PubSubBackend interface
using the nats-py library. It bridges the gap between NATS's async API and the
synchronous PubSubBackend interface by running an event loop in a background thread.

The NATSPubSub class supports queue groups for load balancing, TLS/SSL encryption,
and various authentication methods including username/password, tokens, NKeys, and JWT.

Example:
    Basic usage with local NATS::

        from msight_core.pubsub import NATSPubSub
        from msight_core.pubsub.utils import get_nats_config

        config = get_nats_config(group_id="my_queue_group")
        nats = NATSPubSub(config)

        # Subscribe to a topic with queue group
        nats.subscribe(topic)

        # Listen for messages
        for message in nats.listen():
            print(f"Received: {message}")

        # Publish a message
        nats.publish(topic, b"Hello, NATS!")

    With authentication and TLS::

        import os
        os.environ["MSIGHT_NATS_SERVERS"] = "['nats://server1:4222', 'nats://server2:4222']"
        os.environ["MSIGHT_NATS_USERNAME"] = "user"
        os.environ["MSIGHT_NATS_PASSWORD"] = "pass"
        os.environ["MSIGHT_NATS_USE_TLS"] = "true"

        config = get_nats_config(group_id="processors")
        nats = NATSPubSub(config)

Architecture:
    The class uses a background thread to run an asyncio event loop, allowing
    the async NATS client to operate alongside synchronous code. Messages are
    transferred from the async callback to the synchronous :meth:`listen` method
    via a thread-safe queue.

See Also:
    - :func:`msight_core.pubsub.utils.get_nats_config`: Configuration helper
    - :class:`msight_core.pubsub.base.PubSubBackend`: Base interface
"""

import asyncio
from threading import Thread
from queue import Queue
from nats.aio.client import Client as NATS
from .base import PubSubBackend


class NATSPubSub(PubSubBackend):
    """NATS pub/sub backend using nats-py with async-to-sync bridge.

    This class implements the PubSubBackend interface for NATS messaging,
    running an asyncio event loop in a background thread to handle the
    async NATS client operations. It supports queue groups for distributed
    processing and various authentication/encryption options.

    The class creates a persistent NATS connection on initialization and
    maintains it throughout the application lifecycle. Messages received
    from subscriptions are queued and yielded through the :meth:`listen`
    method.

    Attributes:
        group_id (str or None): Queue group name for load-balanced subscriptions.
        servers (list): List of NATS server URLs.
        nc (NATS): NATS async client instance.
        queue (Queue): Thread-safe queue for passing messages from async to sync.
        topic (Topic or None): Currently subscribed topic object.
        loop (asyncio.AbstractEventLoop): Event loop running in background thread.
        _thread (Thread): Background daemon thread running the event loop.

    Args:
        config (dict): Configuration dictionary containing NATS settings.
            Required keys:

            - ``servers`` (list): List of NATS server URLs (e.g., ``['nats://localhost:4222']``)

            Optional keys:

            - ``group_id`` (str): Queue group name for load balancing
            - ``user`` (str): Username for authentication
            - ``password`` (str): Password for authentication
            - ``token`` (str): Token for authentication
            - ``nkeys_seed`` (str): NKey seed for authentication
            - ``user_jwt`` (str): JWT token for authentication
            - ``user_credentials`` (str): Path to credentials file
            - ``tls`` (bool): Enable TLS/SSL
            - ``tls_ca_cert`` (str): Path to CA certificate
            - ``tls_cert`` (str): Path to client certificate
            - ``tls_key`` (str): Path to client key
            - ``tls_verify`` (bool): Verify server certificate

    Raises:
        Exception: If connection to NATS servers fails.

    Example:
        Initialize with minimal configuration::

            config = {
                'servers': ['nats://localhost:4222']
            }
            nats = NATSPubSub(config)

        Initialize with queue group and authentication::

            config = {
                'servers': ['nats://server:4222'],
                'group_id': 'workers',
                'user': 'myuser',
                'password': 'mypassword',
                'tls': True
            }
            nats = NATSPubSub(config)

    Note:
        The background thread and event loop are started automatically during
        initialization. The connection is established synchronously before
        __init__ returns.
    """
    def __init__(self, config):
        """Initialize NATS pub/sub backend.

        Creates a NATS client, starts a background thread with an event loop,
        and establishes a connection to the NATS servers. This method blocks
        until the connection is successfully established.

        Args:
            config (dict): NATS configuration dictionary.

        Raises:
            Exception: If connection to NATS servers fails.
        """
        self.config = config  # Store full config for connection
        self.group_id = config.get('group_id', None)
        self.servers = config['servers']
        self.nc = NATS()
        self.queue = Queue()
        self.topic = None

        # Start background thread and event loop
        self.loop = asyncio.new_event_loop()
        self._thread = Thread(target=self._start_loop, daemon=True)
        self._thread.start()

        # Connect asynchronously
        fut = asyncio.run_coroutine_threadsafe(self._connect(), self.loop)
        fut.result()  # block until connected

    def _start_loop(self):
        """Start and run the asyncio event loop in the background thread.

        This internal method sets the event loop for the current thread
        and runs it indefinitely. It's executed in a daemon thread.
        """
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _connect(self):
        """Establish connection to NATS servers.

        This coroutine connects to the NATS cluster with all configured
        authentication and TLS options. It's called from the background
        event loop.

        Raises:
            Exception: If connection fails or authentication is rejected.
        """
        # Build connection options from config
        connect_opts = {
            'servers': self.servers
        }
        
        # Authentication options
        if 'user' in self.config:
            connect_opts['user'] = self.config['user']
        if 'password' in self.config:
            connect_opts['password'] = self.config['password']
        if 'token' in self.config:
            connect_opts['token'] = self.config['token']
        if 'nkeys_seed' in self.config:
            connect_opts['nkeys_seed'] = self.config['nkeys_seed']
        if 'user_jwt' in self.config:
            connect_opts['user_jwt'] = self.config['user_jwt']
        if 'user_credentials' in self.config:
            connect_opts['user_credentials'] = self.config['user_credentials']
        
        # TLS options
        if self.config.get('tls', False):
            connect_opts['tls'] = True
            if 'tls_ca_cert' in self.config:
                connect_opts['tls_ca_cert'] = self.config['tls_ca_cert']
            if 'tls_cert' in self.config:
                connect_opts['tls_client_cert'] = self.config['tls_cert']
            if 'tls_key' in self.config:
                connect_opts['tls_client_key'] = self.config['tls_key']
            if 'tls_verify' in self.config:
                connect_opts['tls_verify'] = self.config['tls_verify']
        
        await self.nc.connect(**connect_opts)  

    def subscribe(self, topic):
        """Subscribe to a NATS topic for consuming messages.

        Creates a subscription to the specified topic, optionally using a
        queue group for load-balanced message distribution across multiple
        subscribers. Received messages are placed in an internal queue for
        retrieval via :meth:`listen`.

        When a ``group_id`` is configured, NATS will distribute messages
        among all subscribers in that queue group, enabling horizontal
        scaling and load balancing.

        Note:
            This method must be called before :meth:`listen`.

        Args:
            topic (Topic): Topic object containing the topic name and configuration.

        Example:
            Subscribe to a topic without queue group::

                nats.subscribe(topic)

            Subscribe with queue group (configured in constructor)::

                config = get_nats_config(group_id="workers")
                nats = NATSPubSub(config)
                nats.subscribe(topic)  # Uses "workers" queue group
        """
        self.topic = topic

        async def cb(msg):
            """Callback for incoming messages."""
            self.queue.put(msg.data)

        async def do_subscribe():
            """Subscribe asynchronously with optional queue group."""
            # Use queue group if group_id is set
            if self.group_id:
                await self.nc.subscribe(topic.name, queue=self.group_id, cb=cb)
            else:
                await self.nc.subscribe(topic.name, cb=cb)

        asyncio.run_coroutine_threadsafe(do_subscribe(), self.loop).result()

    def publish(self, topic, serialized_data):
        """Publish a message to a NATS topic.

        Sends serialized data to the specified topic. This method blocks
        until the publish operation completes in the background event loop.

        In NATS, publishing is fire-and-forget by default. The message is
        sent to all subscribers of the topic (or distributed among queue
        group members if applicable).

        Args:
            topic (Topic): Topic object containing the topic name.
            serialized_data (bytes): Serialized message payload to publish.

        Example:
            Publish a message::

                from msight_core.data import SensorData
                data = SensorData(sensor_name="camera1")
                nats.publish(topic, data.serialize())
        """
        async def do_publish():
            """Publish asynchronously."""
            await self.nc.publish(topic.name, serialized_data)

        asyncio.run_coroutine_threadsafe(do_publish(), self.loop).result()

    def listen(self):
        """Listen for messages from the subscribed topic.

        Yields messages as they arrive from the NATS topic. This is a blocking
        generator that retrieves messages from an internal queue populated by
        the async subscription callback.

        The method blocks on the queue until a message is available, making it
        efficient for continuous message processing.

        Note:
            :meth:`subscribe` must be called before using this method.

        Yields:
            bytes (bytes): Serialized message data received from the topic.

        Example:
            Process messages in a loop::

                nats.subscribe(topic)
                for message_data in nats.listen():
                    data = SensorData.deserialize(message_data)
                    print(f"Received from {data.sensor_name}")

            With error handling::

                try:
                    for message_data in nats.listen():
                        process_message(message_data)
                except KeyboardInterrupt:
                    logger.info("Shutting down...")
        """
        while True:
            yield self.queue.get()

