from .base import SinkNode, NodeConfig
import ipaddress
import socket

class IFMSinkNode(SinkNode):
    default_configs = NodeConfig(
        heartbeat_tolerance=-1,
    )
    def __init__(self, configs, header_file, rsu_addr, rsu_port, use_ipv6=False):
        super().__init__(configs)
        self.header_file = header_file
        self.header = open(header_file, "r").read()
        self.rsu_addr = rsu_addr    
        self.rsu_port = rsu_port
        self.use_ipv6 = use_ipv6
        try:
            ip_obj = ipaddress.ip_address(rsu_addr)
            self.use_ipv6 = ip_obj.version == 6
        except ValueError:
            pass

    def send_to_rsus(self, message):
        family = socket.AF_INET6 if self.use_ipv6 else socket.AF_INET
        s = socket.socket(family, socket.SOCK_DGRAM)
        if self.use_ipv6:
            sockaddr = (self.rsu_addr, self.rsu_port, 0, 0)
        else:
            sockaddr = (self.rsu_addr, self.rsu_port)
        s.sendto(message.encode(), sockaddr)
        s.close()

    def on_message(self, data):
        payload = data.data
        payload_hex = payload.hex()
        ifm_message = self.header + payload_hex
        self.send_to_rsus(ifm_message)
        self.logger.info(f"Sent IFM message to RSU {self.rsu_addr}:{self.rsu_port}.")
    @classmethod
    def create(cls, name, subscribe_topic, header_file, rsu_addr, rsu_port, gap=0, use_ipv6=False):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic,
            gap=gap,
            subscribe_topic_data_type=None,
        )
        return cls(
            configs=configs,
            header_file=header_file,
            rsu_addr=rsu_addr,
            rsu_port=rsu_port,
            use_ipv6=use_ipv6,
        )
        
