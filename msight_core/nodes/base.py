"""Base node classes for MSight.

This module provides core base classes used by MSight components:

- :class:`~msight_core.nodes.base.Node` — Generic node that manages
  configuration, registration in Redis, heartbeat monitoring, and
  pub/sub backend selection.

- :class:`~msight_core.nodes.base.SourceNode` — Base for nodes that produce
  data (source/sensor nodes). Implements a simple iterate/publish loop.

- :class:`~msight_core.nodes.base.DataProcessingNode` — Base for nodes that
  subscribe to a topic, process incoming messages and publish
  results to another topic.

- :class:`~msight_core.nodes.base.SinkNode` — Specialized processing node that
  subscribes but does not publish (useful for consumers that only ingest
  messages for storage or side-effects).

Usage
-----
Subclass the appropriate base class and implement the lifecycle methods such
as :meth:`iterate` (for sources) or :meth:`process` (for processing nodes).
Nodes automatically register themselves in Redis and start a background
heartbeat monitor. Configure the pub/sub backend via the
``MSIGHT_PUBSUB_BACKEND`` environment variable (supported backends: ``redis``, 
``nats``, ``kafka``).

Autosummary
-----------
To include a clickable list of the base classes in Sphinx-generated docs, add
an autosummary entry in your documentation. Example::

    .. autosummary::
       :toctree: _autosummary
       :nosignatures:

       Node
       SourceNode
       DataProcessingNode
       SinkNode

"""

from ..data import Data, SensorData
from ..topics import get_topic
# from ..pubsub import RedisPubSub, NATSPubSub
from . import MSIGHT_EDGE_DEVICE_NAME
from msight_core.utils import get_redis_client
from . import REDIS_NODES_FIELD
# import redis
import json
from typing import Union
from enum import Enum, auto
import time
import threading
import os
import signal
from .utils import create_logger, Counter
from typing import Union
from dataclasses import dataclass, fields, replace
from .. import LOGGING_LEVEL

@dataclass
class NodeConfig:
    """Configuration container for nodes.
    Attributes:
        name (str | None): The name of the node.
        publish_topic_name (str | None): The name of the publish topic.
        subscribe_topic_name (str | None): The name of the subscribe topic.
        publish_topic_data_type (str | None): The data type of the publish topic.
        subscribe_topic_data_type (type | None): The data type of the subscribe topic.
    """
    name: str | None = None
    publish_topic_name: str | None = None
    subscribe_topic_name: str | None = None
    publish_topic_data_type: str | None = None
    subscribe_topic_data_type:  type | None = None # class
    heartbeat_update_interval: int | None = None
    action_on_error: str | None = None
    heartbeat_tolerance: float | None = None
    heartbeat_checking_duration: float | None = None
    gap: int | None = None
    group_id: str | None = None
    sensor_name: str | None = None
    logging_level: str | None = "INFO"

    def update(self, cfg):
        if cfg is None:
            return
        for f in fields(self):
            v = getattr(cfg, f.name, None)
            if v is not None:
                setattr(self, f.name, v)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def copy(self):
        return replace(self)

    def __repr__(self):
        attrs = {f.name: getattr(self, f.name) for f in fields(self) if getattr(self, f.name) is not None}
        inner = ", ".join(f"{k}={v}" for k, v in attrs.items())
        return f"NodeConfig({inner})"


class NodeStatus(Enum):
    """The status of the node. The status of the node can be one of the following:
    REGISTERED: The node is registered in the system.
    RUNNING: The node is running.
    STOPPED: The node is stopped.
    ERROR: The node is in error state.
    """
    REGISTERED = auto()
    RUNNING = auto()
    STOPPED = auto()
    ERROR = auto()


# class NodeRegisteredError(Exception):
#     """Exception raised when the node is already registered in the system.

#     Args:
#         Exception (_type_): _description_
#     """
#     def __init__(self, message):
#         self.message = message
#         super().__init__(self.message)


class Node:
    """
    The base Node class.

    Attributes:
        name (str): Name of the node, this is the unique identifier for each node.
        publish_topic (Topic or list(Topic)): The topic(s) that the node will publish to.
        subscribe_topic (Topic): The topic that the node will subscribe to.
        redis_client (redis.Redis): The Redis client that the node will use to communicate with the Redis database.
        configs (NodeConfig): The configurations for the node.
    """
    default_configs = NodeConfig(
        heartbeat_checking_duration=15,
        heartbeat_update_interval=10,
        action_on_error="stop",
        heartbeat_tolerance=15,
        gap=0,
    )

    def __init__(
        self, configs: NodeConfig
    ):
        self.configs = getattr(self, 'combined_configs', self.default_configs).copy()
        self.configs.update(configs)
        assert self.configs.name is not None, "Node name must be provided in the configs."
        self.name = self.configs.name
        self.group_id = self.configs.get('group_id', None)
        logging_level = self.configs.get('logging_level', LOGGING_LEVEL)
        self.logger = create_logger(self.name, logging_level=logging_level)
        self.redis_client = get_redis_client()
        self.publish_topic_name = self.configs.publish_topic_name
        if self.publish_topic_name is not None:
            assert self.configs.publish_topic_data_type is not None, "publish_topic_data_type must be provided if publish_topic is provided."
            self.publish_topic = get_topic(self.redis_client, self.publish_topic_name, register_if_not_exist=True, data_type=self.configs.publish_topic_data_type)
            self.publish_topic_data_type = self.configs.publish_topic_data_type
        else:
            self.publish_topic = None

        self.subscribe_topic_name = self.configs.subscribe_topic_name
        if self.subscribe_topic_name is not None:
            # assert configs.subscribe_topic_data_type is not None, "subscribe_topic_data_type must be provided if subscribe_topic is provided."
            data_type = self.configs.subscribe_topic_data_type if self.configs.subscribe_topic_data_type is not None else SensorData
            self.subscribe_topic = get_topic(self.redis_client, self.subscribe_topic_name, register_if_not_exist=True, data_type=data_type)
            self.subscribe_topic_data_type = self.subscribe_topic.data_type
        else:
            self.subscribe_topic = None
        
        # self.subscribe_topic = get_topic(self.redis_client, self.subscribe_topic_name) if self.subscribe_topic_name is not None else None
        pubsub_backend = os.getenv("MSIGHT_PUBSUB_BACKEND", "redis").lower()
        if pubsub_backend == "redis":
            from ..pubsub import RedisPubSub
            self.pubsub = RedisPubSub(self.redis_client)
        elif pubsub_backend == "nats":
            from ..pubsub import NATSPubSub
            from ..pubsub.utils import get_nats_config
            nats_config = get_nats_config(self.group_id)
            self.pubsub = NATSPubSub(nats_config)
        elif pubsub_backend == "kafka":
            from ..pubsub import KafkaPubSub
            from ..pubsub.utils import get_kafka_config
            group_id = self.group_id if self.group_id is not None else self.name + "_group"
            kafka_config = get_kafka_config(group_id)
            self.pubsub = KafkaPubSub(kafka_config)
        
        # seconds
        self.heartbeat_update_interval = self.configs.heartbeat_update_interval
        self.action_on_error = self.configs.action_on_error

        assert self.action_on_error in [
            "stop", "continue"], "action_on_error should be either 'stop' or 'continue'."
        # seconds
        self.heartbeat_tolerance = self.configs.heartbeat_tolerance
        # seconds
        self.heartbeat_checking_duration = self.configs.heartbeat_checking_duration
        self.heartbeat_counter = Counter(self.heartbeat_update_interval)
        self.register()
        self.on_register()
        # check if the topics are already registered
        # if publish_topic is not None:
        #     self.register_topic(publish_topic)
        # if subscribe_topic is not None:
        #     self.register_topic(subscribe_topic)
        heartbeat_monitor_thread = threading.Thread(
            target=self._heartbeat_monitor, daemon=True)
        heartbeat_monitor_thread.start()

    @classmethod
    def __init_subclass__(cls, **kwargs):
        ## Combine parent and subclass default_configs
        super().__init_subclass__(**kwargs)
        ## 1. Get parent combined configs or parent default configs
        parent_configs = getattr(cls, 'combined_configs', cls.default_configs).copy()
        ## 2. Get subclass default configs
        subclass_configs = getattr(cls, 'default_configs', NodeConfig()).copy()
        ## 3. Combine them
        parent_configs.update(subclass_configs)
        cls.combined_configs = parent_configs
        # print(f"Combined configs for {cls.__name__}: {cls.combined_configs}")

    def update_status(self, status: NodeStatus):
        """Update the status of the node. This method will also update the status in the Redis database that stores the node's status.

        Args:
            status (NodeStatus): The status of the node.
        """
        self.status = status
        node_info = self.redis_client.hget(REDIS_NODES_FIELD, self.name)
        if node_info is not None:
            node_info = json.loads(node_info)
            node_info["status"] = status.name
            self.redis_client.hset(REDIS_NODES_FIELD,
                                   self.name, json.dumps(node_info))
        else:
            self.logger.warning(
                f"Node {self.name} is not registered, cannot update status.")

    def on_register(self):
        """ This is the lifecycle method that will be called when the node is registered.
        """
        pass

    def on_unregister(self):
        """ This is the lifecycle method that will be called when the node is unregistered.
        """
        pass

    def on_before_spin(self):
        """ This is the lifecycle method that will be called before the node starts spinning.
        """
        pass

    def on_before_iteration(self):
        """ This is the lifecycle method that will be called before each iteration.
        """
        pass

    def on_after_iteration(self):
        """ This is the lifecycle method that will be called after each iteration.
        """
        pass

    def iterate(self):
        """ This is the method that will be called in each iteration of the node.
        """
        raise NotImplementedError(
            "This method should be implemented by the subclass.")
    
    def on_before_heartbeat(self):
        """ This is the lifecycle method that will be called before each heartbeat update.
        """
        pass

    def on_before_publish(self, data: Union[Data, list[Data]]):
        """ This is the lifecycle method that will be called before each publish event.
        """
        pass

    def get_registered_info(self):
        """Get the registered information of the node from the Redis database.
        Returns:
            dict: The registered information of the node.
        """
        return self.redis_client.hget(REDIS_NODES_FIELD, self.name)

    def _kill_process(self):
        """Kill the process of the node. This method will be called when the node is stopped due to inactivity or error.
        
        Uses multiple strategies to ensure the process terminates:
        1. SIGTERM - graceful termination
        2. SIGKILL - forceful termination (cannot be caught)
        3. os._exit() - immediate process exit, bypasses all cleanup
        """
        self.logger.warning(f"Forcefully terminating process {os.getpid()}")
        
        # Try SIGTERM first for graceful shutdown
        try:
            os.kill(os.getpid(), signal.SIGTERM)
        except OSError:
            pass
        
        # Give it a brief moment to terminate
        time.sleep(0.1)
        
        # If still alive, try SIGKILL (cannot be caught or ignored)
        try:
            os.kill(os.getpid(), signal.SIGKILL)
        except (OSError, AttributeError):
            pass
        
        # If we're still here, use os._exit() as the nuclear option
        # This immediately terminates the process without any cleanup
        self.logger.error(f"Process {os.getpid()} did not terminate, forcing exit...")
        os._exit(1)

    def _heartbeat_monitor(self):
        """The heartbeat monitor that checks the heartbeat of the node and take actions based on the heartbeat tolerance and action on error configurations. This method runs in a separate thread.
        """
        while True:
            time.sleep(self.heartbeat_checking_duration)
            info = self.get_registered_info()
            if info is not None:
                info = json.loads(info)
                last_heartbeat = info["last_heartbeat"]
                # only when tolerance is larger than 0 we check the heartbeat
                if self.heartbeat_tolerance > 0 and time.time() - last_heartbeat > self.heartbeat_tolerance:
                    # if time.time() - last_heartbeat > self.heartbeat_tolerance:
                    # node is dead
                    self.logger.error(
                        f"Node {self.name} is not sending heartbeat, it may be dead.")
                    self.update_status(NodeStatus.ERROR)
                    if self.action_on_error == "stop":
                        self.logger.error(
                            f"Stopping node {self.name} due to its inactivity.")
                        self.unregister()
                        self._kill_process()
                        return  # Exit the monitor thread after killing the process
                else:
                    self.update_status(NodeStatus.RUNNING)
            else:
                self.logger.error(
                    f"Node {self.name} is not registered, it may be dead.")
                self.update_status(NodeStatus.ERROR)
                if self.action_on_error == "stop":
                    self.unregister()
                    self._kill_process()
                    return  # Exit the monitor thread after killing the process

    def spin(self, life_span: int = -1):
        """Start the node to spin.

        Args:
            life_span (int, optional): How many iterations will the node to spin. Defaults to -1. If life_span is -1, the node will spin indefinitely. The main loop of the node will be in the _spin method.
        """
        self.on_before_spin()
        self.update_status(NodeStatus.RUNNING)
        
        try:
            self._spin(life_span=life_span)
        finally:
            self.unregister()
            self.on_unregister()
            # self.update_status(NodeStatus.STOPPED)

    def _spin(self, life_span: int = -1):
        """The main loop of the node.

        Args:
            life_span (int, optional): How many iterations will the node spin. Defaults to -1.
        """
        life_counter = Counter(life_span)
        while True:
            self.on_before_iteration()
            self.iterate()
            self.on_after_iteration()
            if life_counter.countdown():
                break
            # update heartbeat
            if self.heartbeat_counter.countdown():
                self.heartbeat()

        self.unregister()

    def publish(self, data: Union[Data, list[Data]]):
        """Publish the data to the publish topic of the node.

        Args:
            data (Union[Data, list[Data]]): The data should either be a instance of Data or a list of Data. If the data is a list, it will be published sequentially.
        """
        assert (
            self.publish_topic is not None
        ), "This node does not have a publish topic."

        self.on_before_publish(data)

        def _publish(data):
            # start = time.time()
            if isinstance(data, list):
                for d in data:
                    self.pubsub.publish(self.publish_topic, d.serialize())
            else:
                self.pubsub.publish(self.publish_topic, data.serialize())
            # print(f"publishing time is {time.time() - start}")
        x = threading.Thread(target=_publish, args=(data,), daemon=True)
        x.start()

    def register(self):
        """Register the node to the Redis database that stores the node information. This method will be called when the node is initialized. The node will be registered with the status of REGISTERED.
        """
        # first check if node exists
        if self.redis_client.hexists(REDIS_NODES_FIELD, self.name):
            self.logger.warning(
                f"The node {self.name} already registered with the same name, this can be caused because of the node not exiting normally, or you are using the same node name for multiple node.")
        self.status = NodeStatus.REGISTERED
        info = {
            "name": self.name,
            "device": MSIGHT_EDGE_DEVICE_NAME,
            "publish_topic": None,
            "subscribe_topic": None,
            "type": self.__class__.__name__,
            "last_heartbeat": time.time(),
            "status": self.status.name,
        }
        if self.publish_topic is not None:
            if isinstance(self.publish_topic, list):
                info["publish_topic"] = list(
                    map(lambda x: x.name, self.publish_topic))
            else:
                info["publish_topic"] = self.publish_topic.name
        if self.subscribe_topic is not None:
            info["subscribe_topic"] = self.subscribe_topic.name
        self.redis_client.hset(REDIS_NODES_FIELD,
                               self.name, json.dumps(info))

    def _heartbeat(self):
        """Send heartbeat to the Redis database that stores the node information. This method runs in a separate thread.
        """
        self.on_before_heartbeat()
        node_info_json = self.redis_client.hget(REDIS_NODES_FIELD, self.name)
        node_info = json.loads(node_info_json)
        node_info["last_heartbeat"] = time.time()
        self.redis_client.hset(REDIS_NODES_FIELD,
                               self.name, json.dumps(node_info))

    def heartbeat(self):
        """Send heartbeat to the Redis database that stores the node information. This method will be called in each iteration of the node.
        """
        heartbeat_thread = threading.Thread(
            target=self._heartbeat, daemon=True)
        heartbeat_thread.start()

    def unregister(self):
        """Unregister the node from the Redis database that stores the node information. This method will be called when the node stops spinning. If the node is not unregistered, the node will still be registered in the Redis database.
        """
        self.redis_client.hdel(REDIS_NODES_FIELD, self.name)
        self.logger.info(f"Node {self.name} is unregistered.")

    # def register_topic(self, topic: Topic):
    #     register_topic(self.redis_client, topic)
    #     self.logger.info(f"Node {self.name} is registered.")


class SourceNode(Node):
    """The base class for source nodes. Source nodes are nodes that gets data into the MSight system.
    """
    default_configs = NodeConfig(
        heartbeat_update_interval=10,
        action_on_error="stop",
        heartbeat_tolerance=60,
        heartbeat_checking_duration=15,
        gap=0,
    )

    def __init__(self, configs: NodeConfig):
        super().__init__(configs=configs)
        sensor_name = self.configs.get('sensor_name', 'default_sensor')
        assert sensor_name is not None, "sensor_name must be provided in the configs for SourceNode."
        self.sensor_name = sensor_name
        self.gap = self.configs.gap
        self.gap_counter = Counter(self.gap+1)

    def get_data(self) -> Data:
        """Get the data from the sensor.

        Returns:
            Data: The data from the sensor.
        """
        raise NotImplementedError(
            "This method should be implemented by the subclass.")

    def post_process(self, data: Data) -> Data:
        """Post process the data before publishing.

        Args:
            data (Data): The data received from sensor.

        Returns:
            Data: The data processed.
        """
        return data

    def iterate(self):
        """ The iterate method for the source node. This method will be called in each iteration of the node. It will get data from the sensor, post process the data, and publish the data to the publish topic(s) of the node.
        """
        data = self.get_data()
        if self.gap_counter.countdown():
            data = self.post_process(data)
            self.publish(data)


class DataProcessingNode(Node):
    default_configs = NodeConfig(
        heartbeat_update_interval=10,
        action_on_error="stop",
        heartbeat_tolerance=-1,
        heartbeat_checking_duration=15,
        gap=0,
    )
    """The base class for data processing nodes. Data processing nodes are nodes that process data from a topic and publish the processed data to another topic.
    """

    def __init__(
        self, configs: NodeConfig
    ):
        super().__init__(
            configs=configs
        )
        # self.pubsub = self.redis_client.pubsub()
        self.gap = self.configs.gap
        self.gap_counter = Counter(self.gap+1)

    def process(self, data: Data) -> Union[Data, None]:
        """Process the data from the subscribe topic.

        Args:
            data (Data): The data from the subscribe topic.


        Returns:
            Union[Data, None]: The processed data. If the processed data is None, the node will not publish the data.
        """
        raise NotImplementedError(
            "This method should be implemented by the subclass.")

    def _spin(self, life_span: int = -1):
        """ The main loop of the node. This method will be called when the node is spinning.

        Args:
            life_span (int, optional):  Defaults to -1.
        """
        life_counter = Counter(life_span)
        try:
            self.pubsub.subscribe(self.subscribe_topic)
            self.update_status(NodeStatus.RUNNING)
            for message in self.pubsub.listen():
                self.on_before_iteration()
                data = self.subscribe_topic_data_type.deserialize(message)
                if self.gap_counter.countdown():
                    processed_data = self.process(data)
                    if processed_data is not None:
                        self.publish(processed_data)
                        self.on_after_iteration()
                if life_counter.countdown():
                    break
                # update heartbeat

                if self.heartbeat_counter.countdown():
                    self.heartbeat()

        except KeyboardInterrupt:
            print("Interrupted by user, stopping listener.")


class SinkNode(DataProcessingNode):
    """ Sink node is a special case of DataProcessingNode
     It is a node that only subscribes to a topic and does not publish to any topic """

    def __init__(self, configs):
        super().__init__(configs=configs)

    def on_message(self, data: Union[Data, bytes]):
        """This method will be called when the node receives a message from the subscribe topic.

        Args:
            data (Union[Data, bytes]): The data received from the subscribe topic.
        """
        raise NotImplementedError(
            "This method should be implemented by the subclass.")

    def process(self, data: Data) -> Union[Data, None]:
        """Process the data from the subscribe topic.

        Args:
            data (Data): The data from the subscribe topic.

        Returns:
            Union[Data, None]: The processed data. If the processed data is None, the node will not publish the data.
        """
        self.on_message(data)
        return None

