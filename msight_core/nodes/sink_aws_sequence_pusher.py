from .base import SinkNode, NodeConfig
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from msight_core import MSIGHT_EDGE_DEVICE_NAME
from datetime import datetime
import json
from botocore.config import Config

class AWSSequencePusherSinkNode(SinkNode):
    """
    Push data to AWS, for video data, see AWSVideoPusherSinkNode
    """
        
    def __init__(self, configs, bucket_name, s3_prefix="", aws_region="us-east-1", use_dualstack_endpoint=True):
        super().__init__(configs)
        self.bucket_name = bucket_name
        self.s3_prefix = s3_prefix.rstrip('/')  # Remove trailing slash if any
        s3_config = Config(
            s3={
                'use_dualstack_endpoint': use_dualstack_endpoint,
            }
        )
        self.s3_client = boto3.client('s3', region_name=aws_region, config=s3_config)

    def on_message(self, data):
        self.logger.info("Receive data for uploading.")
        sensor_name = data.sensor_name
        timestamp = data.capture_timestamp
        # print("beg: ", beg, "end: ", end)
        obj_list = data.obj_list
        beg = obj_list[0].capture_timestamp
        end = obj_list[-1].capture_timestamp
        # print("beg: ", beg, "end: ", end)

        ts = datetime.fromtimestamp(timestamp)
        date_str = ts.strftime("%Y-%m-%d")
        hour_str = ts.strftime("%H")

        key = f"{self.s3_prefix}/{MSIGHT_EDGE_DEVICE_NAME}/{sensor_name}/{date_str}/{hour_str}/{int(beg)}_{int(end)}.json"

        try:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=key, Body=json.dumps(data.to_dict()).encode('utf-8'))
            self.logger.info(f"Uploaded data for sensor '{sensor_name}' to S3://{self.bucket_name}/{key}")
        except (NoCredentialsError, ClientError) as e:
            self.logger.error(f"Failed to upload data for sensor '{sensor_name}': {e}")

    @classmethod
    def create(cls, name, subscribe_topic, bucket_name, s3_prefix="", aws_region="us-east-1", use_dualstack_endpoint=True):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic,
        )
        return cls(
            configs,
            bucket_name,
            s3_prefix=s3_prefix,
            aws_region=aws_region,
            use_dualstack_endpoint=use_dualstack_endpoint
        )

