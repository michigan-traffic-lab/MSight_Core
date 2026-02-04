from importlib import import_module
import redis
import os
import yaml
import ast

REDIS_MESSAGE_BROKER_HOST = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_HOST", "localhost")
REDIS_MESSAGE_BROKER_PORT = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_PORT", 6379)
REDIS_MESSAGE_BROKER_DB = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_DB", 0)
REDIS_MESSAGE_BROKER_USERNAME = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_USERNAME", None)
REDIS_MESSAGE_BROKER_PASSWORD = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_PASSWORD", None)
REDIS_MESSAGE_BROKER_USE_TLS = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_USE_TLS", "false").lower() in ["true", "1", "yes"]
REDIS_MESSAGE_BROKER_TLS_CERT_FILE = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_TLS_CERT_FILE", None)
REDIS_MESSAGE_BROKER_TLS_KEY_FILE = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_TLS_KEY_FILE", None)
REDIS_MESSAGE_BROKER_TLS_CA_CERT_FILE = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_TLS_CA_CERT_FILE", None)
REDIS_MESSAGE_BROKER_USE_CLUSTER = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_USE_CLUSTER", "false").lower() in ["true", "1", "yes"]
REDIS_MESSAGE_BROKER_CLUSTER_NODES = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_CLUSTER_NODES", None)
REDIS_MESSAGE_BROKER_UNIX_SOCKET_PATH = os.getenv("MSIGHT_REDIS_MESSAGE_BROKER_UNIX_SOCKET_PATH", None)
MSIGHT_EDGE_DEVICE_NAME = os.getenv("MSIGHT_EDGE_DEVICE_NAME")


def get_class_path(cls):
    module = cls.__module__
    class_name = cls.__name__
    return f"{module}.{class_name}"


def dynamic_import(class_path):
    module_path, class_name = class_path.rsplit('.', 1)
    module = import_module(module_path)
    return getattr(module, class_name)

def get_redis_client()-> redis.Redis | redis.RedisCluster:
    """Get a Redis client with support for various configurations.
    
    Supports:
    - Unix socket connections
    - TCP connections (standalone)
    - Redis Cluster mode
    - Username/password authentication
    - TLS/SSL connections with optional client certificates
    
    Environment Variables:
        MSIGHT_REDIS_MESSAGE_BROKER_UNIX_SOCKET_PATH: Path to Unix socket (takes precedence)
        MSIGHT_REDIS_MESSAGE_BROKER_USE_CLUSTER: Enable cluster mode ("true"/"1"/"yes")
        MSIGHT_REDIS_MESSAGE_BROKER_CLUSTER_NODES: Cluster nodes as list string 
            (e.g., "['host1:6379', 'host2:6379']")
        MSIGHT_REDIS_MESSAGE_BROKER_HOST: Redis host (default: localhost)
        MSIGHT_REDIS_MESSAGE_BROKER_PORT: Redis port (default: 6379)
        MSIGHT_REDIS_MESSAGE_BROKER_DB: Database number (default: 0, ignored in cluster mode)
        MSIGHT_REDIS_MESSAGE_BROKER_USERNAME: Redis username (optional)
        MSIGHT_REDIS_MESSAGE_BROKER_PASSWORD: Redis password (optional)
        MSIGHT_REDIS_MESSAGE_BROKER_USE_TLS: Enable TLS/SSL ("true"/"1"/"yes")
        MSIGHT_REDIS_MESSAGE_BROKER_TLS_CERT_FILE: Client certificate file path (optional)
        MSIGHT_REDIS_MESSAGE_BROKER_TLS_KEY_FILE: Client key file path (optional)
        MSIGHT_REDIS_MESSAGE_BROKER_TLS_CA_CERT_FILE: CA certificate file path (optional)
    
    Returns:
        redis.Redis | redis.RedisCluster: Configured Redis client
    """ 
    # Unix socket connection (highest priority)
    if REDIS_MESSAGE_BROKER_UNIX_SOCKET_PATH is not None:
        return redis.Redis(
            unix_socket_path=REDIS_MESSAGE_BROKER_UNIX_SOCKET_PATH,
            username=REDIS_MESSAGE_BROKER_USERNAME,
            password=REDIS_MESSAGE_BROKER_PASSWORD,
            db=REDIS_MESSAGE_BROKER_DB
        )
    
    # Prepare common connection parameters
    connection_kwargs = {
        "username": REDIS_MESSAGE_BROKER_USERNAME,
        "password": REDIS_MESSAGE_BROKER_PASSWORD,
    }
    
    # TLS/SSL configuration
    if REDIS_MESSAGE_BROKER_USE_TLS:
        ssl_config = {
            "ssl": True,
            "ssl_cert_reqs": "required",
        }
        
        if REDIS_MESSAGE_BROKER_TLS_CA_CERT_FILE:
            ssl_config["ssl_ca_certs"] = REDIS_MESSAGE_BROKER_TLS_CA_CERT_FILE
        
        if REDIS_MESSAGE_BROKER_TLS_CERT_FILE:
            ssl_config["ssl_certfile"] = REDIS_MESSAGE_BROKER_TLS_CERT_FILE
        
        if REDIS_MESSAGE_BROKER_TLS_KEY_FILE:
            ssl_config["ssl_keyfile"] = REDIS_MESSAGE_BROKER_TLS_KEY_FILE
        
        connection_kwargs.update(ssl_config)
    
    # Cluster mode
    if REDIS_MESSAGE_BROKER_USE_CLUSTER:
        if REDIS_MESSAGE_BROKER_CLUSTER_NODES:
            try:
                cluster_nodes_list = ast.literal_eval(REDIS_MESSAGE_BROKER_CLUSTER_NODES)
                if not isinstance(cluster_nodes_list, list):
                    raise ValueError
                
                # Parse host:port strings into startup_nodes format
                startup_nodes = []
                for node in cluster_nodes_list:
                    if isinstance(node, str) and ":" in node:
                        host, port = node.rsplit(":", 1)
                        startup_nodes.append({"host": host.strip(), "port": int(port)})
                    else:
                        raise ValueError(f"Invalid cluster node format: {node}")
                
                connection_kwargs["startup_nodes"] = startup_nodes
            except Exception as e:
                raise ValueError(
                    f"MSIGHT_REDIS_MESSAGE_BROKER_CLUSTER_NODES must be a list like "
                    f"\"['host1:6379', 'host2:6379']\", got {REDIS_MESSAGE_BROKER_CLUSTER_NODES}. "
                    f"Error: {e}"
                )
        else:
            # Use single host:port as cluster entry point
            connection_kwargs["host"] = REDIS_MESSAGE_BROKER_HOST
            connection_kwargs["port"] = int(REDIS_MESSAGE_BROKER_PORT)
        
        return redis.RedisCluster(**connection_kwargs)
    
    # Standard standalone connection
    connection_kwargs.update({
        "host": REDIS_MESSAGE_BROKER_HOST,
        "port": int(REDIS_MESSAGE_BROKER_PORT),
        "db": int(REDIS_MESSAGE_BROKER_DB)
    })
    
    return redis.Redis(**connection_kwargs)

def parse_configs(config_path):
    with open(config_path, 'r') as f:
        configs = yaml.safe_load(f)
    return configs

def get_default_arg_parser(description, node_class):
    from .nodes import SourceNode, DataProcessingNode, SinkNode, Node
    import argparse
    # check the node is source, processing or sink node
    if issubclass(node_class, SourceNode):
        node_type = "source"
    elif issubclass(node_class, SinkNode):
        node_type = "sink"
    elif issubclass(node_class, DataProcessingNode):
        node_type = "processing"
    elif issubclass(node_class, Node):
        node_type = "node"
    else:
        raise ValueError(f"node_class must be a subclass of Node, got {node_class}")
    # print(node_type)
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--name",
        "-n",
        type=str,
        help="Name of the node",
        required=True,
    )
    parser.add_argument(
        "--heartbeat-update-interval",
        type=int,
        help="Heartbeat update interval in seconds",
    )
    parser.add_argument(
        "--action-on-error",
        type=str,
        choices=["continue", "stop"],
        default="stop",
        help="Action to take on error",
    )
    parser.add_argument(
        "--heartbeat-tolerance",
        type=float,
        help="Heartbeat tolerance in seconds",
    )
    parser.add_argument(
        "--heartbeat-checking-duration",
        type=float,
        help="Heartbeat checking duration in seconds",
    )
    parser.add_argument(
        "-g","--gap",
        type=int,
        help="number of messages to skip between two processed messages",
    )
    parser.add_argument(
        "--group-id",
        type=str,
        help="Group ID for message broker (for processing and sink nodes)",
    )
    parser.add_argument(
        '--logging-level',
        type=str,
        default="INFO",
        help='Logging level. One of DEBUG, INFO, WARNING, ERROR, CRITICAL.'
    )

    if node_type in ["source", "processing"]:
        parser.add_argument(
            "--publish-topic", "-pt",
            type=str,
            required=True,
            help="Publish topic name",
        )
    if node_type in ["processing", "sink"]:
        parser.add_argument(
            "--subscribe-topic", "-st",
            type=str,
            required=True,
            help="Subscribe topic name",
        )
    if node_type == "processing":
        parser.add_argument(
            "--sensor-name", "-sn",
            type=str,
            help="Sensor name",
        )
    if node_type == "source":
        parser.add_argument(
            "--sensor-name", "-sn",
            type=str,
            required=True,
            help="Sensor name",
        )
    return parser

def get_node_config_from_args(args):
    from .nodes.base import NodeConfig
    config_kwargs = {}
    for field in NodeConfig.__dataclass_fields__.keys():
        arg_value = getattr(args, field, None)
        if arg_value is not None:
            config_kwargs[field] = arg_value
    if hasattr(args, "publish_topic") and args.publish_topic is not None:
        config_kwargs["publish_topic_name"] = args.publish_topic
    if hasattr(args, "subscribe_topic") and args.subscribe_topic is not None:
        config_kwargs["subscribe_topic_name"] = args.subscribe_topic
    return NodeConfig(**config_kwargs)

