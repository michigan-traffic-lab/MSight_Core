from msight_core.nodes import BytesViewerSinkNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args


def main():
    parser = get_default_arg_parser(description="Launch an bytes viewer source node.", node_class=BytesViewerSinkNode)
    parser.add_argument("--filter-sensor-name", type=str, default=None, help="the sensor name you want")
    args = parser.parse_args()
    configs = get_node_config_from_args(args)
    node = BytesViewerSinkNode(configs, filter_sensor_name=args.filter_sensor_name)
    node.spin()


if __name__ == "__main__":
    main()

