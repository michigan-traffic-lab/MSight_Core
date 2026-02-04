from msight_core.utils import get_default_arg_parser, get_node_config_from_args
from msight_core.nodes import HttpSinkNode
import time

def main():
    parser = get_default_arg_parser(description="Launch an HTTP sink node.", node_class=HttpSinkNode)
    parser.add_argument(
        "-u", "--url", required=True, type=str, help="The url to send the data to."
    )
    parser.add_argument(
        "--partition-key-mode",
        default="random",
        choices=["random", "sensor_name"],
        type=str,
        help='The partition key mode to use, use "random" or "sensor_name".',
    )
    parser.add_argument("-w", "--wait", type=int, default=0,
                        help="The wait time in seconds before starting the node.")
    parser.add_argument("--shards", type=int, default=1,
                        help="The number of shards to use when partition_key_mode is 'sensor_name'.")
    args = parser.parse_args()
    assert args.partition_key_mode in ["random", "sensor_name"]
    time.sleep(args.wait)
    configs = get_node_config_from_args(args)
    sink_node = HttpSinkNode(
        configs,
        url=args.url,
        partition_key_mode=args.partition_key_mode,
        shards=args.shards,
    )
    sink_node.spin()

