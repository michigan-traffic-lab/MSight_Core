from .base import SinkNode, NodeConfig
from ..data import BytesData
import time

class BytesViewerSinkNode(SinkNode):
    def __init__(self, configs, filter_sensor_name=None):
        super().__init__(configs)
        self.filter_sensor_name = filter_sensor_name

    @classmethod
    def create(cls, name, subscribe_topic_name, filter_sensor_name=None):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic_name,
            subscribe_topic_data_type=BytesData
        )
        return cls(configs=configs, filter_sensor_name=filter_sensor_name)

    def on_message(self, data):
        payload = data.bytes
        event_timestamp = data.event_timestamp
        latency = (time.time() - event_timestamp) * 1000
        sensor_name = data.sensor_name
        if self.filter_sensor_name is not None and self.filter_sensor_name != sensor_name:
            return 
        self.logger.info(f"Bytes received, latency: {latency: .0f} ms, sensor_name: {sensor_name}")
        self.logger.info(f"Payload: {payload}")


