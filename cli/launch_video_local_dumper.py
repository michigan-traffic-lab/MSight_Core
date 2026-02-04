from msight_core.nodes import VideoLocalDumperSinkNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args


def main():
    parser = get_default_arg_parser(
        description="Launch a Video Local Dumper sink node.",
        node_class=VideoLocalDumperSinkNode
    )
    parser.add_argument(
        "--save-dir", "-sd",
        type=str,
        required=True,
        help="Directory to save dumped videos",
    )
    args = parser.parse_args()
    configs = get_node_config_from_args(args)
    sink_node = VideoLocalDumperSinkNode(
        configs,
        save_dir=args.save_dir
    )
    sink_node.spin()
    
if __name__ == "__main__":
    main()
