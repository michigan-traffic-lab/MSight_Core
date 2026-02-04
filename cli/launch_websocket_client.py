from msight_core.nodes import WebSocketClientSourceNode
from msight_core.utils import get_node_config_from_args, get_default_arg_parser


def main():
    parser = get_default_arg_parser(
        description="Launch a source node to receive SDSM messages.",
        node_class=WebSocketClientSourceNode
    )
    parser.add_argument("-u", "--server-url", required=True, help="The url of the WebSocket server")
    args = parser.parse_args()
    configs = get_node_config_from_args(args)
    source_node = WebSocketClientSourceNode(
        configs,
        server_url=args.server_url
    )
    print(f"Starting the WebSocket Client Source node {configs.name}.")
    source_node.spin()


if __name__ == "__main__":
    main()
