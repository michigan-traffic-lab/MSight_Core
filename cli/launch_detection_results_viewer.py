from msight_core.nodes import DetectionResultsSinkNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args


def main():
    parser = get_default_arg_parser(
        description='Launch an image viewer source node.', node_class=DetectionResultsSinkNode)
    args = parser.parse_args()
    configs = get_node_config_from_args(args)
    node = DetectionResultsSinkNode(configs)
    node.spin()

if __name__ == "__main__":
    main()

