from msight_core.nodes import PointCloudLocalDumperSinkNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args

def main():
    argparser = get_default_arg_parser(description="Launch Point Cloud Local Dumper Sink Node, this node saves point cloud data to local folder.", node_class=PointCloudLocalDumperSinkNode)
    argparser.add_argument("--output-folder-path", required=True, help="Output folder path to save point cloud data")
    argparser.add_argument("--use-creation-timestamp", action="store_true", help="Use creation timestamp instead of capture time for file naming")
    args = argparser.parse_args()
    configs = get_node_config_from_args(args)
    point_cloud_sink = PointCloudLocalDumperSinkNode(
        configs,
        args.output_folder_path, 
        use_creation_timestamp=args.use_creation_timestamp
   )
    point_cloud_sink.spin()
if __name__ == "__main__":
    main()

