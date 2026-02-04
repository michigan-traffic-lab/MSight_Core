from msight_core.nodes import IFMSinkNode
from pathlib import Path
from msight_core.utils import get_default_arg_parser, get_node_config_from_args

def main():
    argparser = get_default_arg_parser(description="Launch a node to send Immediate Forwarding Message to RSU.", node_class=IFMSinkNode)
    argparser.add_argument("--header-file", required=True, type=Path, help="The file containing the header.")
    argparser.add_argument("--rsu-addr", required=True, type=str, help="The address of the RSU.")
    argparser.add_argument("--rsu-port", required=True, type=int, help="The port of the RSU.")
    argparser.add_argument("--ipv6", action='store_true', help="Use IPv6 to connect to RSU.")
    args = argparser.parse_args()
    # use absolute path for header file
    header_file = args.header_file.resolve()
    configs = get_node_config_from_args(args)
    sink_node = IFMSinkNode(configs, header_file, args.rsu_addr, args.rsu_port, use_ipv6=args.ipv6)
    print(f"Starting the IFM Sink node {args.name}.")
    sink_node.spin()

