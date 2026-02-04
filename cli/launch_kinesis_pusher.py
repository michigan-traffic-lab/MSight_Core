from msight_core.nodes import KinesisPusherSinkNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args
import time


def main():
    parser = get_default_arg_parser(description="Launch an HTTP sink node.", node_class=KinesisPusherSinkNode)
    parser.add_argument(
        "--partition-key-mode",
        default="random",
        choices=["random", "sensor_name"],
        type=str,
        help='The partition key mode to use, use "random" or "sensor_name".',
    )
    parser.add_argument("--stream-name", required=True, type=str)
    parser.add_argument("--shards", type=int, default=1,
                        help="The number of shards in the Kinesis stream (used when partition key mode is 'sensor_name'). It will rotate through the shards.")
    parser.add_argument("-w", "--wait", type=int, default=0,
                        help="The wait time in seconds before starting the node.")
    args = parser.parse_args()
    assert args.partition_key_mode in ["random", "sensor_name"]
    time.sleep(args.wait)
    configs = get_node_config_from_args(args)
    sink_node = KinesisPusherSinkNode(configs, args.stream_name, args.partition_key_mode, args.shards)
    sink_node.spin()

