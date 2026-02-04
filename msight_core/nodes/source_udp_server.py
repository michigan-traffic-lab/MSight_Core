import socketserver
import socket
from ..data.bytes import BytesData
from .base import NodeConfig
from .source_server import ServerSourceNode  # or from . import ServerSourceNode
import time


class _UdpServer(socketserver.ThreadingUDPServer):
    """
    Thin wrapper so the handler can access the node instance via self.server.node.
    """
    allow_reuse_address = True

    def __init__(self, server_address, handler_class, node: "UdpServerSourceNode", address_family=socket.AF_INET):
        self.address_family = address_family
        super().__init__(server_address, handler_class)
        self.node = node


class UdpServerSourceNode(ServerSourceNode):
    """
    A generic UDP server node implemented using socketserver.
    """
    default_configs = NodeConfig(
        heartbeat_tolerance=-1,
        publish_topic_data_type=BytesData,
    )
    def __init__(
        self,
        configs: NodeConfig,
        host: str,
        port: int,
        ipv6: bool = False,
    ):
        super().__init__(configs=configs)  # this will call self.initialize()
        self.ipv6 = ipv6
        self.host = host if host else ("::" if ipv6 else "0.0.0.0")
        self.port = port
        self._server = None
        

    # ------------------------------------------------------------------
    # Factory method
    # ------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        name: str,
        publish_topic_name: str,
        sensor_name: str,
        gap: int = 0,
        host: str = "0.0.0.0",
        port: int = 5000,
        ipv6: bool = False
    ) -> "UdpServerSourceNode":
        """
        Convenience factory, matching your base class API.
        Adjust NodeConfig(...) if your signature differs.
        """
        configs = NodeConfig(
            name=name,
            publish_topic_name=publish_topic_name,
            publish_topic_data_type=BytesData,
            gap=gap,
            sensor_name=sensor_name,
        )
        return cls(configs=configs, host=host, port=port, ipv6=ipv6)

    # ------------------------------------------------------------------
    # ServerSourceNode abstract methods
    # ------------------------------------------------------------------
    def initialize(self):
        """
        Called by ServerSourceNode.__init__.

        Here we:
        - Build the socketserver handler class.
        - Instantiate the UDP server and store it in self._server.
        """
        handler_cls = self._make_handler_class()
        family = socket.AF_INET6 if self.ipv6 else socket.AF_INET
        self._server = _UdpServer((self.host, self.port), handler_cls, self, address_family=family)

    def serve(self):
        """
        Blocking server loop. Called by _spin()/spin()/start().
        """
        if self._server is None:
            raise RuntimeError("UDP server not initialized. Did initialize() run?")

        try:
            self.logger.info(f"UDP server listening on {self.host}:{self.port}...")
            self._server.serve_forever()
        finally:
            self._server.server_close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _make_handler_class(self):
        """
        Creates a per-node handler class that forwards datagrams to
        self.handle_incoming().
        """
        node = self

        class UdpRequestHandler(socketserver.BaseRequestHandler):
            def handle(self):
                raw_data, sock = self.request  # type: ignore[assignment]
                # Convert raw bytes -> BytesData
                # Hand off to the generic source-node handler
                node.handle_incoming(raw_data)
                # node.logger.info(f"Received data of size {len(raw_data)}, publishing to {node.publish_topic.name}.")

        return UdpRequestHandler
    
    def on_message(self, raw_data):
        data_obj = BytesData(
            data=raw_data, 
            capture_timestamp=time.time(), 
            creation_timestamp=time.time(),
            sensor_name=self.sensor_name)
        self.logger.info(f"Received UDP data of size {len(raw_data)}, publishing to {self.publish_topic.name}.")
        return data_obj


