from msight_core.nodes import AWSSNSPusherSinkNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args


def main():
    parser = get_default_arg_parser(
        description="Launch AWS SNS Pusher Sink Node. Publishes subscribed data to an SNS topic with filterable message attributes (sensor_name, device_name, capture_timestamp, creation_timestamp).",
        node_class=AWSSNSPusherSinkNode,
    )
    parser.add_argument(
        "--topic-arn",
        type=str,
        required=True,
        help="ARN of the SNS topic to publish to.",
    )
    parser.add_argument(
        "--use-dualstack-endpoint",
        action="store_true",
        help="Use dualstack endpoint for the SNS client.",
    )

    args = parser.parse_args()
    configs = get_node_config_from_args(args)

    node = AWSSNSPusherSinkNode(
        configs,
        args.topic_arn,
        use_dualstack_endpoint=args.use_dualstack_endpoint,
    )
    node.spin()


if __name__ == "__main__":
    main()
