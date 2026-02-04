""" This module contains the classes for the nodes that are used in the MSight Edge pipeline.
"""

from .. import REDIS_MESSAGE_BROKER_HOST, REDIS_MESSAGE_BROKER_PORT, REDIS_MESSAGE_BROKER_DB, MSIGHT_EDGE_DEVICE_NAME
REDIS_NODES_FIELD="MSIGHT:NODES"
from .base import Node, SourceNode, SinkNode, DataProcessingNode, NodeConfig
from .source_rtsp import RTSPSourceNode
from .source_local_image import LocalImageSourceNode
from .source_velodyne_lidar import VelodyneLidarSourceNode
from .source_server import ServerSourceNode
from .sink_image_viewer import ImageViewerSinkNode
from .sink_http import HttpSinkNode
from .source_downloaded_image_player import DownloadedImagePlayerSourceNode
from .source_websocket import WebSocketClientSourceNode
from .sink_bytes_viewer import BytesViewerSinkNode
from .sink_detection_results_viewer import DetectionResultsSinkNode
from .sink_ifm import IFMSinkNode
from .sink_pointcloud_viewer import PointCloudViewerSinkNode
from .sink_pointcloud_local_dumper import PointCloudLocalDumperSinkNode
from .sink_kinesis_pusher import KinesisPusherSinkNode
try:
    from .data_process_sdsm_encoder import SDSMEncoderNode
except ImportError:
    print(f"Waining: SDSMEncoderNode not imported. Please install the required dependencies.")
except RuntimeError:
    print(f"Waining: SDSMEncoderNode not imported. Please install the required dependencies.")
from .data_process_buffering_sort import BufferingSortNode
# from .data_process_road_user_list_aggregator import RoadUserListAggregatorNode
from .data_process_image_to_video_aggregator import ImageToVideoAggregatorNode
from .data_process_aggregator import AggregatorNode
# from .source_derq import DerqSourceNode
# from .source_tscbm import TSCBMSourceNode
from .source_udp_server import UdpServerSourceNode
from .sink_video_local_dumper import VideoLocalDumperSinkNode
from .sink_aws_video_pusher import AWSVideoPusherSinkNode
from .sink_aws_sequence_pusher import AWSSequencePusherSinkNode
from .sink_image_local_dumper import ImageLocalDumperSinkNode
# from .source_ouster import OusterSourceNode # do not import this node because some of the dependencies are not installed in some of the Docker images
# from .source_mcity_spat import MCitySpatSourceNode
# from .source_socketIO import SocketIOSourceNode

