from .base import SourceNode, NodeConfig
from ..data import ImageData
import cv2
import time
from datetime import datetime
from pathlib import Path

class LocalImageSourceNode(SourceNode):
    '''A dummy source node that publishes images from a local directory
       if the path is a directory, it will circulate through all the images in the directory
       otherwise, it will only publish the image periodically
    '''
    default_configs = NodeConfig(
        publish_topic_data_type=ImageData,
    )
    def __init__(self, configs, image_path, fps=10):
        super().__init__(configs)
        self.image_path = Path(image_path)

        if self.image_path.is_dir():
            # list all .jpg and .png files
            self.images = list(self.image_path.glob("*.jpg")) + list(self.image_path.glob("*.png"))
            # then sort them
            self.images.sort()
        elif self.image_path.is_file():
            self.images = [self.image_path]
        else:
            raise ValueError("image_path must be a directory or an image file, check the path.")

        self.counter = 0

        self.fps = fps
        # self.sensor_type = "testing_image"

    def get_data(self):
        time.sleep(1/self.fps)

        img = cv2.imread(str(self.images[self.counter % len(self.images)]))
        img_data = ImageData.from_ndarray(
            img,
            sensor_name=self.sensor_name,
            capture_timestamp=time.time(),
            creation_timestamp=time.time(),
        )
        self.counter += 1
        self.counter %= len(self.images)
        self.logger.info(f"sent image from {self.sensor_name}, the immage shape is {img.shape}, time: {img_data.time}")
        return img_data
    
    @classmethod
    def create(cls, name, publish_topic_name, sensor_name, image_path, fps=10):
        configs = NodeConfig(
            name=name,
            publish_topic_name=publish_topic_name,
            sensor_name=sensor_name,
        )
        return cls(configs, image_path, fps)
