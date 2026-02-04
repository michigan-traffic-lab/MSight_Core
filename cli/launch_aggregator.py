from msight_core.nodes import AggregatorNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args

def main():
    parser = get_default_arg_parser(description="Launch Detection Results Aggregator Node", node_class=AggregatorNode)
    parser.add_argument("--buffer-size", type=int, required=True, help="Buffer size for the aggregator")
    parser.add_argument("--overlap-size", type=int, required=True, help="Overlap size for the aggregator")
    args = parser.parse_args()
    # Create the detection results aggregator node
    configs = get_node_config_from_args(args)
    node = AggregatorNode(
        configs,
        buffer_size=args.buffer_size,
        overlap_size=args.overlap_size,
    )
    node.spin()

if __name__ == "__main__":
    main()
    
