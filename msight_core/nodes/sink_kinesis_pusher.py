import boto3
import os
region_name = os.environ.get('AWS_REGION', 'us-east-1')
kinesis_client = boto3.client('kinesis', region_name=region_name)
from msight_core.nodes import SinkNode
import time
import threading
from .base import NodeConfig

class KinesisPusherSinkNode(SinkNode):
    def __init__(self, configs: NodeConfig, stream_name: str, partition_key_mode: str = "random", shards: int = 1):
        super().__init__(configs)
        self.stream_name = stream_name
        self.partition_key_mode = partition_key_mode
        self.shards = shards
        assert self.partition_key_mode in ["random", "sensor_name"]
        self.shard_counter = 0

    # def on_message(self, data):
    #     x = threading.Thread(target=self._on_message, args=(data,))
    #     x.daemon = True
    #     x.start()

    def on_message(self, data):
        # print("on_message", data.sensor_name)
        if self.partition_key_mode == 'random':
            pk = str(time.time())
        elif self.partition_key_mode == 'sensor_name':
            self.shard_counter += 1
            if self.shard_counter % self.shards == 0:
                self.shard_counter = 0
            pk = data.sensor_name  + str(self.shard_counter)
        data_json = data.to_json()
        def kinesis_put_record():
            res = kinesis_client.put_record(
                StreamName=self.stream_name,
                Data=data_json,
                PartitionKey=pk
            )
            # print(data_json)
            self.logger.info(f"Published to {self.stream_name}, partition key {pk}, sequence number {res['SequenceNumber']}.")
        x = threading.Thread(target=kinesis_put_record)
        x.daemon = True
        x.start()

