from msight_core.nodes import AWSSequencePusherSinkNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args

def main():
    parser = get_default_arg_parser(description="Launch AWS Sequence Pusher Sink Node", node_class=AWSSequencePusherSinkNode)
    parser.add_argument("--bucket-name", type=str, required=True, help="AWS Bucket name")
    parser.add_argument("--prefix", type=str, default="", help="S3 prefix for the objects")
    parser.add_argument("--aws-region", type=str, default="us-east-1", help="AWS region")
    parser.add_argument("--use-dualstack-endpoint", action="store_true", help="Use dualstack endpoint")

    args = parser.parse_args()
    configs = get_node_config_from_args(args)

    # Create the AWS Sequence Pusher sink node

    node = AWSSequencePusherSinkNode(
        configs, args.bucket_name, s3_prefix=args.prefix, aws_region=args.aws_region, use_dualstack_endpoint=args.use_dualstack_endpoint
    )
    node.spin()

if __name__ == "__main__":
    main()


