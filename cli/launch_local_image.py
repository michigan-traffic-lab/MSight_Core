from msight_core.nodes import LocalImageSourceNode
from msight_core.utils import get_node_config_from_args, get_default_arg_parser


def main():
    parser = get_default_arg_parser(
        description='Launch a dummy local image source node.', node_class=LocalImageSourceNode)
    parser.add_argument('-p', '--image-path', type=str,
                        required=True, help='The path to the image file.')
    parser.add_argument('--fps', type=int, default=10,
                        help='The frame rate of the image source.')
    args = parser.parse_args()

    configs = get_node_config_from_args(args)
    source_node = LocalImageSourceNode(
        configs, args.image_path, args.fps)
    print(f"Starting the dummy local image source node {args.name}.")
    source_node.spin()


if __name__ == "__main__":
    main()

