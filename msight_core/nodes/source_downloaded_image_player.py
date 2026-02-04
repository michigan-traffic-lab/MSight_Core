from .base import SourceNode, NodeConfig
from ..data import ImageData
import cv2
import time
from datetime import datetime
from pathlib import Path
import cv2


def get_timestamp(filename):
    """Extract datetime object from filename."""
    try:
        return datetime.strptime(filename, "%Y-%m-%d %H-%M-%S-%f.jpg")
    except ValueError as e:
        print(f"Error parsing datetime from {filename}: {e}")
        return None
    
def get_all_timestamps(folder_path):
    """Get all timestamps from filenames in a folder."""
    timestamps = []
    for filepath in folder_path.iterdir():
        if filepath.is_file():
            timestamp = get_timestamp(filepath.name)
            if timestamp:
                timestamps.append((timestamp, filepath))
    return sorted(timestamps)

def binary_search_closest(sorted_list, target):
    """Find the index of the closest value to the target in a sorted list."""
    low, high = 0, len(sorted_list) - 1
    best_index = low
    while low <= high:
        mid = (low + high) // 2
        if sorted_list[mid][0] < target:
            low = mid + 1
        elif sorted_list[mid][0] > target:
            high = mid - 1
        else:
            return mid  # Exact match found
        # Update best_index if this element is closer to the target
        if abs(sorted_list[mid][0] - target) < abs(sorted_list[best_index][0] - target):
            best_index = mid
    return best_index

def find_closest_image(target_timestamp, sorted_timestamps):
    """Find the closest image in time given sorted timestamps."""
    closest_index = binary_search_closest(sorted_timestamps, target_timestamp)
    return sorted_timestamps[closest_index]

class DownloadedImagePlayerSourceNode(SourceNode):
    '''
    A source node that publishes images from downloaded directory using msight_download_data
    '''
    default_configs = NodeConfig(
        publish_topic_data_type=ImageData,
        sensor_name="downloaded_image_player",
    )
    def __init__(self, configs, root, fps=10, primary_sensor=None, time_mode='local'):
        super().__init__(configs)
        # print(f"Downloaded image player source node: {name}")
        self.root = Path(root)
        self.fps = fps
        self.counter = 0

        self.fps = fps
        # get all directory names
        self.sensors = sorted([x.name for x in self.root.iterdir() if x.is_dir()])
        # self.sensor_type = "testing_image"
        self.primary_sensor = primary_sensor
        if primary_sensor is None:
            self.primary_sensor = self.sensors[0]

        self.sensor_images = {}
        for sensor in self.sensors:
            self.sensor_images[sensor] = get_all_timestamps(self.root / sensor)
        # print(self.sensor_images    )
        self.buffer = []
        self.pointer = 0
        self.time_mode = time_mode
        self.t_start = None
        
    def on_before_spin(self):
        self.logger.info(f"Downloaded image player source node: {self.name} started, publishing to {self.publish_topic.name} at {self.fps} fps. Primary sensor: {self.primary_sensor}")

    def wait_for_next_frame(self):
        t_end = time.time()
        t_elapsed = t_end - self.t_start
        if t_elapsed > 1 / self.fps:
            self.logger.warning(f"Frame rate is too slow: {t_elapsed:.3f}s")
        time.sleep(max(0, 1 / self.fps - t_elapsed))

    def get_data(self):
        if self.buffer:
            data = self.buffer.pop(0)
            if len(self.buffer) == 0:
                self.wait_for_next_frame()
            return data
        else:
            if len(self.sensors) == 1 and self.t_start is not None:
                self.wait_for_next_frame()
        # read image here and topic here
        self.t_start = time.time()  # Start timing
        primary_image_pack = self.sensor_images[self.primary_sensor][self.pointer]
        primary_time = primary_image_pack[0]
        # self.logger.info(f"Reading image {primary_image_pack[1]} at time {primary_time}")
        primary_image = cv2.imread(str(primary_image_pack[1]))
        time_str =str(primary_time) if self.time_mode == 'local' else str(datetime.now())
        primary_img_data = ImageData(primary_image, time_str, self.primary_sensor)



        for sensor in self.sensors:
            if sensor != self.primary_sensor:

                t_start = time.time()  # Start timing

                closest_image_pack = find_closest_image(primary_time, self.sensor_images[sensor])
                closest_time = closest_image_pack[0]
                if abs((closest_time - primary_time).total_seconds()) > 1:
                    print(f"Warning: {sensor} is more than 1 second off from primary sensor, skip this image")
                    continue
                closest_image = cv2.imread(str(closest_image_pack[1]))
                time_str =str(closest_time) if self.time_mode == 'local' else str(datetime.now())
                closest_img_data = ImageData(closest_image, time_str, sensor)

                detection_time = time.time() - t_start  # Calculate detection time
                self.logger.info(f"read one frame from  in {detection_time:.3f} seconds.")


                self.buffer.append(closest_img_data)
        self.pointer += 1
        if self.pointer >= len(self.sensor_images[self.primary_sensor]):
            self.pointer = 0
        return primary_img_data
    
    @classmethod
    def create(cls, name, publish_topic_name, root, fps=10, primary_sensor=None, time_mode='local'):
        configs = NodeConfig(
            publish_topic_name=publish_topic_name,
            name=name,
        )
        return cls(configs, root, fps, primary_sensor, time_mode)

