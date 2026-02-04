from msight_core.nodes import UdpServerSourceNode
from msight_core.utils import get_node_config_from_args, get_default_arg_parser


def main():
    parser = get_default_arg_parser(
        description="Launch a source node to receive SDSM messages.",
        node_class=UdpServerSourceNode
    )
    parser.add_argument("--host", default="0.0.0.0", help="The host to server udp server")
    parser.add_argument(
        "--port", type=int, required=True, help="The port to server udp server"
    )
    parser.add_argument(
        "--ipv6",
        action="store_true",
        help="Use IPv6 for the UDP server. Default is IPv4.",
    )
    args = parser.parse_args()

    configs = get_node_config_from_args(args)
    source_node = UdpServerSourceNode(
        configs,
        host=args.host,
        port=args.port,
        ipv6=args.ipv6
    )
    print(f"Starting the UDP Source node {configs.name}.")
    source_node.spin()


if __name__ == "__main__":
    main()

