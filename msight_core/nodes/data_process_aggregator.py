from .base import DataProcessingNode, NodeConfig
from ..data import SensorData, SensorDataSequence

class AggregatorNode(DataProcessingNode):
    default_configs = NodeConfig(
        publish_topic_data_type=SensorDataSequence,
    )
    def __init__(self, configs, buffer_size, overlap_size,):
        super().__init__(configs)
        self.buffer_size = buffer_size
        self.buffer = {} # sensor_name -> list of SensorData
        if overlap_size > buffer_size:
            raise ValueError("Overlap size must be less than or equal to buffer size.")
        self.overlap_size = overlap_size
        self.initialized = {}

    def initialize(self, sensor_name: str):
        pass

    def aggregate(self, data: SensorData, sensor_name: str):
        self.logger.info(f"Aggregating data for sensor {sensor_name}: {data}")

    def pack_aggregated_data(self, sensor_name: str) -> SensorData:
        return SensorDataSequence(obj_list=self.buffer[sensor_name], sensor_name=sensor_name)

    def aggregate_buffer(self, sensor_name: str):
        self.initialize(sensor_name)
        for data in self.buffer[sensor_name]:
            self.aggregate(data, sensor_name)

    def process(self, data: SensorData):
        sensor_name = data.sensor_name
        if sensor_name not in self.initialized:
            self.initialize(sensor_name)
            self.initialized[sensor_name] = True

        if sensor_name not in self.buffer:
            self.buffer[sensor_name] = []
        self.buffer[sensor_name].append(data)
        self.aggregate(data, sensor_name)
        if len(self.buffer[sensor_name]) >= self.buffer_size:
            result_data = self.pack_aggregated_data(sensor_name)
            # clear the buffer, but keep the overlap portion
            if self.overlap_size > 0:
                self.buffer[sensor_name] = self.buffer[sensor_name][-self.overlap_size:]
            else:
                self.buffer[sensor_name] = []
            # re-aggregate the overlap portion of the buffer
            self.aggregate_buffer(sensor_name)
            self.logger.info(f"Aggregate data for sensor {sensor_name}, {len(self.buffer[sensor_name])} items left in buffer.")
            return result_data
        return None
    
    @classmethod
    def create(cls, buffer_size, overlap_size, name, subscribe_topic, publish_topic):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic,
            publish_topic_name=publish_topic,
        )
        return cls(
            configs,
            buffer_size,
            overlap_size,
        )               
    
