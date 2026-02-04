import requests
import threading

from msight_core.nodes.base import SinkNode, NodeConfig

# from msight_core.data import Data
import time


class HttpSinkNode(SinkNode):
    def __init__(
        self,
        configs,
        url: str,
        headers: dict = None,
        partition_key_mode: str = "random",
        shards = 1,

    ):
        super().__init__(configs=configs)
        self.url = url
        default_headers = {"Content-Type": "application/json"}
        if headers is None:
            self.headers = default_headers
        else:
            self.headers = default_headers.copy()
            self.headers.update(headers)
        self.partition_key_mode = partition_key_mode
        assert self.partition_key_mode in ["random", "sensor_name"]
        self.shards = shards
        self.shard_counter = 0

    @classmethod
    def create(
        cls, name, subscribe_topic_name, url, gap=0, headers=None, partition_key_mode="random", shards=1
    ):
        configs = NodeConfig(name=name, subscribe_topic_name=subscribe_topic_name, gap=gap)
        return cls(
            configs=configs,
            url=url,
            headers=headers,
            partition_key_mode=partition_key_mode,
            shards=shards
        )

    def on_message(self, data):
        if self.partition_key_mode == "random":
            pk = time.time()
        elif self.partition_key_mode == "sensor_name":
            self.shard_counter += 1
            if self.shard_counter % self.shards == 0:
                self.shard_counter = 0
            pk = data.sensor_name + str(self.shard_counter)
        data_json = data.to_json()
        headers = self.headers
        headers["X-Partition-Key"] = str(pk)

        def send_data(data_json, partition_key):
            self.logger.info(f"Sending data to {self.url}... waiting for response")

            # data_size = len(data_json) / 1024
            # self.logger.info(f"data {data_size}kb")
            res = requests.post(
                self.url,
                data=data_json,
                headers=headers,
                params={"partition_key": partition_key},
                timeout=5
            )
            self.logger.info(f"Status: {res.status_code}, {res.text}")

        x = threading.Thread(target=send_data, args=(data_json, pk))

        x.daemon = True
        x.start()
        # self.logger.info(type(data_json))
        # send_data(data_json, pk)

