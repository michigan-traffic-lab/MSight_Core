from msight_core.utils import get_default_arg_parser, get_node_config_from_args
from msight_core.nodes import BufferingSortNode

def main():
    parser = get_default_arg_parser(description="Launch Buffering Sort Node", node_class=BufferingSortNode)

    parser.add_argument('--max-buffer-size', required=False, default=10, type=int,
                        help='The maximum buffer size.')
    args = parser.parse_args()
    configs = get_node_config_from_args(args)
    
    # if pub_topic is None:
    #     pub_topic = Topic(args.publish_topic, SensorData)
    node = BufferingSortNode(
        configs, max_buffer_size=args.max_buffer_size)
    node.spin()


if __name__ == "__main__":
    main()

