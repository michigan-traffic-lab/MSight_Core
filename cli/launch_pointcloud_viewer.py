from msight_core.nodes import PointCloudViewerSinkNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args

def main():
    argparser = get_default_arg_parser(description="Launch Point Cloud Viewer Sink Node, this node visualizes point cloud data.", node_class=PointCloudViewerSinkNode)
    argparser.add_argument("--filter-sensor-name", default=None, help="Filter sensor name")
    argparser.add_argument("--voxel-downsample", type=float, default=None, help="Voxel downsample factor")
    argparser.add_argument("--color-mode", choices=["ring", "intensity"], default="ring", help="Color mode for point cloud")
    args = argparser.parse_args()
    configs = get_node_config_from_args(args)
    point_cloud_sink = PointCloudViewerSinkNode(
        configs,
        filter_sensor_name=args.filter_sensor_name,
        voxel_downsample=args.voxel_downsample,
        color_mode=args.color_mode
   )
    point_cloud_sink.spin()
