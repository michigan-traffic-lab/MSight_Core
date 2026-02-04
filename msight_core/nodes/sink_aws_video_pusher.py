from .base import SinkNode, NodeConfig
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from msight_core import MSIGHT_EDGE_DEVICE_NAME
from datetime import datetime
import json
from botocore.config import Config

class AWSVideoPusherSinkNode(SinkNode):
    def __init__(self, configs:NodeConfig, bucket_name, s3_prefix="", aws_region="us-east-1", use_dualstack_endpoint=True):
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
        video_bytes = data.video
        sensor_name = data.sensor_name
        timestamp = data.creation_timestamp

        timestamps = data.capture_timestamps
        beg = timestamps[0]
        end = timestamps[-1]
        # print("beg: ", beg, "end: ", end)

        ts = datetime.fromtimestamp(timestamp)
        date_str = ts.strftime("%Y-%m-%d")
        hour_str = ts.strftime("%H")

        video_key = f"{MSIGHT_EDGE_DEVICE_NAME}/{sensor_name}/{date_str}/{hour_str}/{int(beg)}_{int(end)}.mp4"
        metadata_key = f"{MSIGHT_EDGE_DEVICE_NAME}/{sensor_name}/{date_str}/{hour_str}/{int(beg)}_{int(end)}.json"
        if self.s3_prefix:
            video_key = f"{self.s3_prefix}/{video_key}"
            metadata_key = f"{self.s3_prefix}/{metadata_key}"
        meta_data = data.to_dict()
        del meta_data['video']  # Remove video bytes from metadata to avoid large payloads

        try:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=video_key, Body=video_bytes)
            self.logger.info(f"Uploaded video for sensor '{sensor_name}' to S3://{self.bucket_name}/{video_key}")
            self.s3_client.put_object(Bucket=self.bucket_name, Key=metadata_key, Body=json.dumps(meta_data).encode('utf-8'))
            self.logger.info(f"Uploaded metadata for sensor '{sensor_name}' to S3://{self.bucket_name}/{metadata_key}")
        except (NoCredentialsError, ClientError) as e:
            self.logger.error(f"Failed to upload video for sensor '{sensor_name}': {e}")

    @classmethod
    def create(cls, name, subscribe_topic, bucket_name, s3_prefix="", aws_region="us-east-1", use_dualstack_endpoint=True,):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic,
        )
        return cls(
            configs,
            bucket_name,
            s3_prefix=s3_prefix,
            aws_region=aws_region,
            use_dualstack_endpoint=use_dualstack_endpoint,
        )

