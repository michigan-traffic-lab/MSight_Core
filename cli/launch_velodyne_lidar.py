from msight_core.nodes import VelodyneLidarSourceNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args


def main():
    parser = get_default_arg_parser(
        description="Launch a Velodyne Lidar source node.",
        node_class=VelodyneLidarSourceNode
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host IP address")
    parser.add_argument("--port", type=int, default=2368, help="Port number")
    parser.add_argument("--ipv6", action="store_true", help="Use IPv6")
    parser.add_argument("--telemetry-port", type=int,
                        default=8308, help="Telemetry port number")
    parser.add_argument("--model-id", default="VLP32C", help="Lidar model ID", choices=[
        "HDL64E_S1", "HDL64E_S2", "HDL64E_S3", "HDL32E",
        "VLP32A", "VLP32B", "VLP32C", "VLP16", "PuckLite", "PuckHiRes", "VLS128", "AlphaPrime"
    ])
    args = parser.parse_args()
    configs = get_node_config_from_args(args)
    source_node = VelodyneLidarSourceNode(
        configs,
        host=args.host,
        port=args.port,
        ipv6=args.ipv6,
        telemetry_port=args.telemetry_port,
        model_id=args.model_id,
    )
    source_node.spin()


if __name__ == "__main__":
    main()

