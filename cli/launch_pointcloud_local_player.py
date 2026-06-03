from msight_core.nodes import LocalPointCloudPlayerSourceNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args


def main():
    argparser = get_default_arg_parser(
        description="Launch Local Point Cloud Player Source Node. "
                    "Replays PCD files dumped by the PointCloudLocalDumperSinkNode.",
        node_class=LocalPointCloudPlayerSourceNode,
    )
    argparser.add_argument(
        "--root", required=True,
        help="Root folder directly above sensor sub-directories "
             "(e.g. output_folder_path/<date>/<hour>/)",
    )
    argparser.add_argument(
        "--fps", type=float, default=10.0,
        help="Replay frame-rate in Hz (default: 10)",
    )
    argparser.add_argument(
        "--primary-sensor", default=None,
        help="Name of the sensor that drives timing. "
             "Defaults to the first sensor found alphabetically.",
    )
    argparser.add_argument(
        "--no-loop", action="store_true",
        help="Stop replaying when the recording ends instead of looping.",
    )
    args = argparser.parse_args()
    configs = get_node_config_from_args(args)
    node = LocalPointCloudPlayerSourceNode(
        configs,
        root=args.root,
        fps=args.fps,
        primary_sensor=args.primary_sensor,
        loop=not args.no_loop,
    )
    node.spin()


if __name__ == "__main__":
    main()
