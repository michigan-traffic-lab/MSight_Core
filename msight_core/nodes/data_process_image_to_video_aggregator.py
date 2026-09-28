import imageio.v3 as iio
import copy
import threading
from .data_process_aggregator import AggregatorNode  # adjust if needed
from ..data import VideoData, ImageData
import cv2
import time
from .base import NodeConfig, NodeStatus

class ImageToVideoAggregatorNode(AggregatorNode):
    default_configs = NodeConfig(
        publish_topic_data_type=VideoData,
    )
    def __init__(
        self,
        configs,
        buffer_size,
        overlap_size,
        fps: int = 30,
        codec: str = "libx265",
        max_consecutive_encode_failures: int = 2,
        # ffmpeg_params: list = None,
    ):
        super().__init__(
            configs,
            buffer_size=buffer_size,
            overlap_size=overlap_size,
        )
        self.fps = fps
        self.codec = codec
        self.asynchronous_packing = True  # Set to True for asynchronous packing
        self.video_buffers = {} # sensor_name -> IOBytes
        self.video_writers = {} # sensor_name -> VideoWriter
        self.frames = {}  # sensor_name -> list of frames
        self.max_consecutive_encode_failures = max_consecutive_encode_failures # <= 0 disables stopping the node
        self.consecutive_encode_failures = 0
        self.encode_failure_lock = threading.Lock() # encoding runs in one thread per packed video
        # if ffmpeg_params is None:
        #     self.ffmpeg_params=["-pix_fmt", "yuv420p"],
        # else:
        #     self.ffmpeg_params = ffmpeg_params

    def initialize(self, sensor_name: str):
        """Initialize the video buffer and writer for the given sensor."""
        self.frames[sensor_name] = []

    def aggregate(self, data: ImageData, sensor_name: str):
        self.logger.info(f"Aggregating image data for sensor: {sensor_name}")
        start = time.time()
        if sensor_name not in self.frames:
            self.initialize(sensor_name)
        image = data.decoded_image
        self.frames[sensor_name].append(image)
        print(f"Time taken to aggregate image: {time.time() - start:.4f} seconds")

    def pack_aggregated_data(self, sensor_name: str):
        """Pack the aggregated frames into a VideoData object."""
        frames = copy.copy(self.frames[sensor_name])  # Copy frames to avoid modifying the original list
        timestamps = [d.capture_timestamp for d in self.buffer[sensor_name]]
        frame_ids = [d.frame_id for d in self.buffer[sensor_name]]
        frames = [cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) for frame in frames] # Convert BGR to RGB for video encoding, imageio expects RGB format
        def _pack_and_send():
            print(f"Packing aggregated data for sensor: {sensor_name}, number of frames: {len(frames)}")
            start = time.time()
            try:
                video_bytes = iio.imwrite(
                    "<bytes>",
                    frames,
                    fps=self.fps,
                    codec=self.codec,
                    extension='.mp4',
                    # ffmpeg_params=self.ffmpeg_params,
                )
            except Exception:
                self.logger.exception(f"Failed to encode video for sensor: {sensor_name} with codec {self.codec}, dropping {len(frames)} frames")
                self.record_encode_result(success=False)
                return
            self.record_encode_result(success=True)
            videoData = VideoData(
                video=video_bytes,
                capture_timestamps=timestamps,
                sensor_name=sensor_name,
                frame_ids=frame_ids
            )
            self.logger.info(f"Time taken to pack video data: {time.time() - start:.4f} seconds")
            self.logger.info(f"Packed video data for sensor: {sensor_name}, size: {len(video_bytes)} bytes")
            self.publish(videoData)
        x = threading.Thread(target=_pack_and_send)
        x.daemon = True
        x.start()

    def record_encode_result(self, success: bool):
        """Stop the node once encoding has failed max_consecutive_encode_failures times in a row.

        A GPU codec such as hevc_nvenc fails on every video once the container has lost access to
        /dev/nvidia* (e.g. after `systemctl daemon-reload` on a host using the systemd cgroup driver),
        and the node would otherwise keep dropping videos forever. Stopping the process lets the
        container restart policy restart the container, which gives it access to the GPU again.
        """
        with self.encode_failure_lock:
            self.consecutive_encode_failures = 0 if success else self.consecutive_encode_failures + 1
            failures = self.consecutive_encode_failures
        if success or failures != self.max_consecutive_encode_failures or self.action_on_error != "stop":
            return
        self.logger.error(f"Video encoding failed {failures} times in a row, stopping node {self.name} so that it can be restarted.")
        try:
            self.update_status(NodeStatus.ERROR)
            self.unregister()
        finally:
            self._kill_process()

    @classmethod
    def create(cls, buffer_size, overlap_size, name, subscribe_topic, publish_topic, fps=30, codec="libx265"):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic,
            publish_topic_name=publish_topic,
        )
        return cls(
            configs, buffer_size, overlap_size, fps=fps, codec=codec
        )

