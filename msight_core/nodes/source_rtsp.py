from .base import SourceNode, NodeConfig
from ..data import ImageData
import time
import cv2
import av


class RTSPSourceNode(SourceNode):
    default_configs = NodeConfig(
        publish_topic_data_type=ImageData
    )
    def __init__(self, configs, url, rtsp_transport="tcp", resize_ratio=None):
        super().__init__(configs)
        self.url = url
        self.resize_ratio = resize_ratio
        self.rtsp_transport = rtsp_transport
        self.logger.info(f"Connecting to RTSP stream at {self.url} using {rtsp_transport} transport...")

    def on_before_spin(self):
        self.container = av.open(
            self.url,
            options={
                "rtsp_transport": self.rtsp_transport,  # try "udp" if you want to experiment
                "max_delay": "0",
            },
        )
        self.stream = self.container.streams.video[0]
        # Create a frame generator so get_data() just asks for "next frame"
        self._frame_iter = self.container.decode(self.stream)

    def _get_raw_frame(self):
        """Get one raw frame from the PyAV stream."""
        try:
            frame = next(self._frame_iter)
        except StopIteration:
            # Stream ended (shouldn't happen with looping RTSP, but be robust)
            self.container.close()
            self.container = av.open(
                self.url,
                options={
                    "rtsp_transport": "tcp",
                    "max_delay": "0",
                },
            )
            self.stream = self.container.streams.video[0]
            self._frame_iter = self.container.decode(self.stream)
            frame = next(self._frame_iter)

        img = frame.to_ndarray(format="bgr24")
        return img

    def get_data(self):
        capture_timestamp = time.time()
        img = self._get_raw_frame()

        if self.resize_ratio != None:
            img = cv2.resize(
                img, (0, 0),
                fx=self.resize_ratio,
                fy=self.resize_ratio,
            )

        # self.logger.info(f"The image shape is {img.shape}")  # maybe log occasionally
        img_data = ImageData.from_ndarray(
            image=img,
            sensor_name=self.sensor_name,
            capture_timestamp=capture_timestamp,
            creation_timestamp=time.time(),
        )
        # (img, str(datetime.now()), self.sensor_name)
        self.logger.info(f"Got image from {self.sensor_name}, the immage shape is {img.shape}, time: {img_data.time}")
        return img_data

    @classmethod
    def create(cls, name, publish_topic_name, sensor_name, url, rtsp_transport="tcp", gap=0, resize_ratio=1.0):
        configs = NodeConfig(
            name=name,
            publish_topic_name=publish_topic_name,
            gap=gap,
            sensor_name=sensor_name,
        )

        return cls(configs=configs, url=url, rtsp_transport=rtsp_transport, resize_ratio=resize_ratio)
