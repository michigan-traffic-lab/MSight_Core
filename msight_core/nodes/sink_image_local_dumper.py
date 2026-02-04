from .base import SinkNode
from .base import NodeConfig
import cv2
from pathlib import Path
from datetime import datetime
import threading

class ImageLocalDumperSinkNode(SinkNode):
    def __init__(self, configs, output_folder_path: str):
        super().__init__(configs)
        self.output_folder_path = Path(output_folder_path)
        self.output_folder_path.mkdir(parents=True, exist_ok=True)

    def on_message(self, data):
        image = data.image # this is a bytes object
        sensor_name = data.sensor_name
        t = datetime.fromtimestamp(data.capture_timestamp)
        timestring = t.isoformat()
        file_path = self.output_folder_path / f"{t.year}-{t.month:02}-{t.day:02}/{t.hour:02}/{data.sensor_name}/{timestring}.jpg".replace(":", "-")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if data.is_encoded:
            def save_image_bytes():
                with open(file_path, 'wb') as f:
                    f.write(image)
            thread = threading.Thread(target=save_image_bytes, daemon=True)
            thread.start()
        else:
            # need to encode the image first
            nparr = data.to_ndarray()
            def save_image_ndarray():
                cv2.imwrite(str(file_path), nparr)
            thread = threading.Thread(target=save_image_ndarray, daemon=True)
            thread.start()
        self.logger.info(f"Saved image for sensor {sensor_name} at {file_path}")

    @classmethod
    def create(cls, name, subscribe_topic, output_folder_path: str):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic,
        )
        return cls(
            configs=configs,
            output_folder_path=output_folder_path,
        )
