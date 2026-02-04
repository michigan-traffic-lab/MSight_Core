from .base import SinkNode
# from ..data import ImageData
from .base import NodeConfig
import cv2
import time
from ..data import ImageData

class ImageViewerSinkNode(SinkNode):
    def __init__(self, configs, filter_sensor_name=None):
        super().__init__(configs)
        self.filter_sensor_name = filter_sensor_name

    def on_message(self, data):
        event_timestamp = data.creation_timestamp
        latency = (time.time() - event_timestamp) * 1000
        image = data.to_ndarray()
        sensor_name = data.sensor_name
        if self.filter_sensor_name is not None and self.filter_sensor_name != sensor_name:
            return 
        self.logger.info(f"Image received, latency: {latency: .0f} ms, sensor_name: {sensor_name}")
        if data.detection_results is not None:
            obj_list = data.detection_results.detection_object_list
            for obj in obj_list:
                center_x = obj['pix_bottom_center_x']
                center_y = obj['pix_bottom_center_y']
                bb_x1 = obj['pix_bb_x1']
                bb_x2 = obj['pix_bb_x2']
                bb_y1 = obj['pix_bb_y1']
                bb_y2 = obj['pix_bb_y2']
                cat = int(obj['category'])
                if cat == 0: #vehicle
                    color=(255,0,0)
                elif cat == 2: #pedestrian
                    color=(128, 128, 0)
                else:
                    color = (0, 0, 0)
                image = cv2.rectangle(image, (bb_x1, bb_y1), (bb_x2, bb_y2), color, 2) 
                image = cv2.circle(image, (center_x, center_y), 3, (237, 237, 50), 2)
        try:
            cv2.imshow(self.name, image)
            cv2.waitKey(1)
        except Exception as e:
            self.logger.warning(f"Error displaying image: {e}")

    @classmethod
    def create(cls, name, subscribe_topic_name, filter_sensor_name=None):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic_name,
            subscribe_topic_data_type=ImageData
        )
        return cls(configs=configs, filter_sensor_name=filter_sensor_name)
        

