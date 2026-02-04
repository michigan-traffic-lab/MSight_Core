from .source_udp_server import UdpServerSourceNode
from ..data import PointCloudData
from .base import NodeConfig
import velodyne_decoder as vd
import time
from datetime import datetime
from .utils import Counter


class VelodyneLidarSourceNode(UdpServerSourceNode):
    default_configs = NodeConfig(
        publish_topic_data_type=PointCloudData,
    )
    def __init__(self, configs,  host, port, ipv6=False, telemetry_port=None,
                 model_id="VLP32C"):
        '''
        A Velodyne Lidar UDP source node.
        Args:
            configs (NodeConfig): Node configuration.
            host (str): Host IP address to bind the UDP server.
            port (int): Port number to bind the UDP server.
            ipv6 (bool): Whether to use IPv6. Default is False.
            telemetry_port (int or None): Port number for telemetry data. Default is None.
            model_id (str): Velodyne model ID, e.g., "VLP32C". Default is "VLP32C". Choices are: "HDL64E_S1", "HDL64E_S2", "HDL64E_S3", "HDL32E", \
                "VLP32A", "VLP32B", "VLP32C", "VLP16", "PuckLite", "PuckHiRes", "VLS128" and "AlphaPrime".
        '''
        super().__init__(configs, host, port, ipv6=ipv6)
        self.lidar_config = vd.Config(model=vd.Model[model_id])
        self.decoder = vd.StreamDecoder(self.lidar_config)
        self.telemetry_port = telemetry_port
        # because the base class uses gap_counter, and in this case, the base class's gap_counter should not be used, instead, we should handler gap ourselves using a different gap_counter_
        if configs.gap is not None and configs.gap > 0:
            self.gap_counter = Counter(0) # disable base class gap counter because this class aggregates packets into point clouds
            self.gap_counter_ = Counter(configs.gap)
        else:
            self.gap_counter_ = Counter(0)  # no gap

    def on_message(self, data):
        start = time.time()
        decoded = self.decoder.decode(time.time(), data, True)
        if decoded is None:
            return
        if self.gap_counter_.countdown():
            timestamps = decoded[0]
            lidar_raw_data = decoded[1]
            lidar_data = PointCloudData.from_ndarray(
                points = lidar_raw_data,
                sensor_name=self.sensor_name,
                capture_timestamp=timestamps.device,
                creation_timestamp=timestamps.host
            )
            end = time.time()
            self.logger.info(
                f"Processed Velodyne Lidar data in {end - start:.2f} seconds, published to the topic {self.publish_topic.name}")
            return lidar_data
        

    @classmethod
    def create(cls, name, publish_topic_name, sensor_name, host, port,
               model_id,  # e.g., "VLP32C"
               ipv6=False, telemetry_port=None):
        return cls(
            name=name,
            publish_topic=publish_topic_name,
            sensor_name=sensor_name,
            host=host,
            port=port,
            ipv6=ipv6,
            telemetry_port=telemetry_port,
            model_id=model_id,
        )

