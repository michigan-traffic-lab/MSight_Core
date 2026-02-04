from msight_core.nodes.source_rtsp import RTSPSourceNode
from msight_core.utils import get_node_config_from_args, get_default_arg_parser


def main():
    parser = get_default_arg_parser(
        description='Launch a source node to grap rtsp stream.', node_class=RTSPSourceNode)
    parser.add_argument('-u', '--url', required=True,
                        help="The url of the RTSP stream")
    # resize_ratio
    parser.add_argument('-r', '--resize-ratio', type=float,
                        help='The ratio to resize the image. Default is 1.0.')
    parser.add_argument('--rtsp-transport', type=str, default="tcp", choices=["tcp", "udp"],
                        help='The RTSP transport protocol, "tcp" or "udp". Default is "tcp".')
    args = parser.parse_args()
    configs = get_node_config_from_args(args)

    # print("hhh" + args.sensor_name)
    source_node = RTSPSourceNode(
        configs,
        url=args.url,
        rtsp_transport=args.rtsp_transport,
        resize_ratio=args.resize_ratio
    )
    print(f"Starting the RTSP Source node {args.name}.")
    source_node.spin()


if __name__ == "__main__":
    main()

