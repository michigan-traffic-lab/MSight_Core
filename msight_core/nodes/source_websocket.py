import websockets
from websockets.exceptions import ConnectionClosedError
import time

from ..data import BytesData
from .base import NodeConfig
from .async_source_node import AsyncSourceNode  # <- the new base class above


class WebSocketClientSourceNode(AsyncSourceNode):
    default_configs = NodeConfig(
        heartbeat_tolerance=-1,
        publish_topic_data_type=BytesData,
    )

    def __init__(self, configs, server_url: str):
        super().__init__(configs)

        self.server_url = server_url
        self.websocket = None  # will be set in _async_setup

        

    # ---------- AsyncSourceNode hooks ----------

    async def _async_setup(self):
        self.logger.info(f"{self.name} connecting to WebSocket {self.server_url}...")
        self.websocket = await websockets.connect(self.server_url)
        self.logger.info(f"{self.name} connected to {self.server_url}.")

    async def _recv_once(self):
        """
        Receive a single message from the WebSocket.

        Raise StopAsyncIteration on disconnect to stop the node.
        """
        try:
            return await self.websocket.recv()
        except ConnectionClosedError:
            self.logger.warning(f"{self.name} disconnected from {self.server_url}.")
            raise StopAsyncIteration

    def on_message(self, data):
        """
        Wrap the received WebSocket message into BytesData.

        If it's a string, we encode as UTF-8.
        If it's already bytes (binary WS message), use as-is.
        """
        if isinstance(data, str):
            payload = data.encode("utf-8")
        else:
            payload = data

        # You can adjust timestamp format as needed
        timestamp = time.time()
        self.logger.info(f"Got data from {self.sensor_name}, size: {len(payload)} bytes, time: {timestamp}")
        return BytesData(
            data=payload,
            capture_timestamp=timestamp,
            sensor_name=self.sensor_name,
            creation_timestamp=time.time(),
        )

    # ---------- Factory method ----------

    @classmethod
    def create(
        cls,
        name: str,
        publish_topic_name: str,
        sensor_name: str,
        server_url: str,
        gap: int = 0,
    ) -> "WebSocketClientSourceNode":
        """
        Convenience factory, matching your base class API.
        """
        configs = NodeConfig(
            name=name,
            publish_topic_name=publish_topic_name,
            publish_topic_data_type=BytesData,
            gap=gap,
            sensor_name=sensor_name,
        )
        return cls(configs=configs, server_url=server_url)
    
