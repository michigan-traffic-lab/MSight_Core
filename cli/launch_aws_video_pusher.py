from msight_core.nodes import AWSVideoPusherSinkNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args
import time

def main():
    argparser = get_default_arg_parser(description="Launch Image to Video Aggregator Node, this node aggregates image data into video data.", node_class=AWSVideoPusherSinkNode)
    argparser.add_argument("--bucket-name", type=str, required=True, help="Name of the S3 bucket to store the video data.")
    argparser.add_argument("--prefix", type=str, default="", help="Prefix for the S3 bucket where video data will be stored.")
    argparser.add_argument("--aws-region", type=str, default="us-east-1", help="AWS region for the S3 bucket.")
    argparser.add_argument("--use-dualstack-endpoint", action='store_true', help="Use dualstack endpoint for S3 client.")
    argparser.add_argument("--wait", "-w", type=int, default=0,
                        help="The wait time in seconds before starting the node.")
    args = argparser.parse_args()
    time.sleep(args.wait)
    # pub_topic = Topic(args.publish_topic, VideoData)
    configs = get_node_config_from_args(args)
    aggregator = AWSVideoPusherSinkNode(
        configs, args.bucket_name, s3_prefix=args.prefix, aws_region=args.aws_region, use_dualstack_endpoint=args.use_dualstack_endpoint
    )

    aggregator.spin()

if __name__ == "__main__":
    main()
