from .base import SinkNode
# from ..data import ImageData

class DetectionResultsSinkNode(SinkNode):
    def __init__(self, configs):
        super().__init__(configs)

    def on_message(self, data):
        self.logger.info(f"Received Detection Result Data of sensor {data.sensor_name}, at time {data.time}, frame_id {data.frame_id}")
        self.logger.info(data.detection_object_list)

