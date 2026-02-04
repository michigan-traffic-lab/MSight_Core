from .base import DataProcessingNode, NodeConfig
from ..data import SensorData
from dataclasses import dataclass, field
from queue import PriorityQueue


@dataclass(order=True)
class Event:
    event_timestamp: float
    obj: object = field(compare=False)

class BufferingSortNode(DataProcessingNode):
    default_configs = NodeConfig(
        heartbeat_tolerance=-1,
        publish_topic_data_type=SensorData,
    )
    def __init__(self, configs:NodeConfig, max_buffer_size=10):
        super().__init__(configs)
        self.buffer = PriorityQueue()
        self.max_buffer_size = max_buffer_size
        # self.max_buffer_size = self.configs["max_buffer_size"]
        # self.equipmentType = self.configs["equipmentType"]

    def process(self, data: SensorData):
        # self.logger.info(f"Received data of size {len(data.detection_object_list)}.")
        assert isinstance(data, SensorData), "Data must be DetectionResultsData"
        self.buffer.put(Event(data.event_timestamp, data))
        self.logger.info(f"Input data to buffer, current buffer size: {self.buffer.qsize()}")
        if self.buffer.qsize() > self.max_buffer_size:
            e = self.buffer.get()
            data = e.obj
            self.logger.info(f"Buffer full, pop out the oldest data. timestamp: {data.event_timestamp}")
            return data
        
    @classmethod
    def create(cls, name, subscribe_topic, publish_topic, max_buffer_size=10):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic,
            publish_topic_name=publish_topic,
            max_buffer_size=max_buffer_size,
        )
        return cls(configs, max_buffer_size=max_buffer_size)
        
        
