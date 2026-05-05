from .base import SinkNode, NodeConfig
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from botocore.config import Config
from msight_core import MSIGHT_EDGE_DEVICE_NAME
import threading
import os

_aws_region = os.environ.get('AWS_REGION', 'us-east-1')


class AWSSNSPusherSinkNode(SinkNode):
    """Publish subscribed data to an AWS SNS topic.

    Each message is sent as the JSON representation of the data object.
    SNS message attributes are attached so that SNS subscription filter
    policies can selectively deliver messages based on:

    - ``sensor_name``   – name of the originating sensor (String)
    - ``device_name``   – value of ``MSIGHT_EDGE_DEVICE_NAME`` (String)
    - ``capture_timestamp``  – epoch timestamp of capture (Number), when present
    - ``creation_timestamp`` – epoch timestamp of message creation (Number), when present
    """

    def __init__(
        self,
        configs: NodeConfig,
        topic_arn: str,
        use_dualstack_endpoint: bool = True,
    ):
        super().__init__(configs)
        self.topic_arn = topic_arn
        self.sns_client = boto3.client(
            "sns",
            region_name=_aws_region,
            config=Config(use_dualstack_endpoint=use_dualstack_endpoint),
        )

    def on_message(self, data):
        message = data.to_json()

        sensor_name = str(getattr(data, "sensor_name", "") or "")
        device_name = str(MSIGHT_EDGE_DEVICE_NAME or "")
        capture_timestamp = getattr(data, "capture_timestamp", None)
        creation_timestamp = getattr(data, "creation_timestamp", None)

        message_attributes = {
            "sensor_name": {
                "DataType": "String",
                "StringValue": sensor_name,
            },
            "device_name": {
                "DataType": "String",
                "StringValue": device_name,
            },
        }

        if capture_timestamp is not None:
            message_attributes["capture_timestamp"] = {
                "DataType": "Number",
                "StringValue": str(capture_timestamp),
            }

        if creation_timestamp is not None:
            message_attributes["creation_timestamp"] = {
                "DataType": "Number",
                "StringValue": str(creation_timestamp),
            }

        def _publish():
            try:
                res = self.sns_client.publish(
                    TopicArn=self.topic_arn,
                    Message=message,
                    MessageAttributes=message_attributes,
                )
                self.logger.info(
                    f"Published to SNS {self.topic_arn}, MessageId: {res['MessageId']}."
                )
            except (NoCredentialsError, ClientError) as e:
                self.logger.error(f"Failed to publish to SNS {self.topic_arn}: {e}")

        t = threading.Thread(target=_publish)
        t.daemon = True
        t.start()

    @classmethod
    def create(
        cls,
        name: str,
        subscribe_topic: str,
        topic_arn: str,
        use_dualstack_endpoint: bool = True,
    ):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic,
        )
        return cls(
            configs,
            topic_arn,
            use_dualstack_endpoint=use_dualstack_endpoint,
        )
