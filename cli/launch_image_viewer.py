from msight_core.nodes import ImageViewerSinkNode
from msight_core.utils import get_node_config_from_args, get_default_arg_parser


def main():
    parser = get_default_arg_parser(description='Launch an image viewer source node.', node_class=ImageViewerSinkNode)

    parser.add_argument("--filter-sensor-name", type=str, default=None, help="the sensor name you want")
    args = parser.parse_args()
    configs = get_node_config_from_args(args)
    source_node = ImageViewerSinkNode(
        configs,
        filter_sensor_name=args.filter_sensor_name
    )
    source_node.spin()


if __name__ == "__main__":
    main()

