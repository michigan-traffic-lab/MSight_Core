from msight_core.nodes import ImageToVideoAggregatorNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args

def main():
    argparser = get_default_arg_parser(description="Launch Image to Video Aggregator Node, this node aggregates image data into video data.", node_class=ImageToVideoAggregatorNode)
    argparser.add_argument("--buffer-size", type=int, required=True, help="Size of the buffer for image aggregation.")
    argparser.add_argument("--overlap-size", type=int, required=True, help="Size of the overlap in the buffer.")
    argparser.add_argument("--fps", type=int, default=20, help="Frames per second for the output video.")
    argparser.add_argument("--codec", type=str, default="libx265", help="Codec to use for video encoding.")
    argparser.add_argument("--max-consecutive-encode-failures", type=int, default=2, help="Stop the node after this many consecutive video encoding failures when --action-on-error is 'stop', so that the container restart policy can restart it (e.g. to regain GPU access). 0 disables it.")
    args = argparser.parse_args()

    configs = get_node_config_from_args(args)
    aggregator = ImageToVideoAggregatorNode(
        configs,
        buffer_size=args.buffer_size,
        overlap_size=args.overlap_size,
        fps=args.fps,
        codec=args.codec,
        max_consecutive_encode_failures=args.max_consecutive_encode_failures,
    )

    aggregator.spin()

if __name__ == "__main__":
    main()

