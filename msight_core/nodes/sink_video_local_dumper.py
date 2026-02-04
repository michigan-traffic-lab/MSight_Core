from msight_core.nodes import SinkNode, NodeConfig
from pathlib import Path
import json

class VideoLocalDumperSinkNode(SinkNode):
    def __init__(self, configs: NodeConfig, save_dir: str):
        super().__init__(configs)
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def on_message(self, data):
        video_bytes = data.video
        sensor_name = data.sensor_name
        save_dir = self.save_dir / sensor_name
        save_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{sensor_name}_{data.capture_timestamp}"
        file_path = save_dir / f"{filename}.mp4"
        with open(file_path, 'wb') as f:
            f.write(video_bytes)
        self.logger.info(f"Saved video for sensor {sensor_name} at {file_path}")
        data_dict = data.to_dict()
        # delete the video bytes to save space
        data_dict['video'] = None
        with open(save_dir / f"{filename}_metadata.json", 'w') as f:
            json.dump(data_dict, f)
