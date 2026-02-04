from msight_core.nodes import SDSMEncoderNode
from msight_core.utils import get_default_arg_parser, get_node_config_from_args
import ast

def main():
    parser = get_default_arg_parser(description="Launch a node to encode detection results to SDSM messages.", node_class=SDSMEncoderNode)
    parser.add_argument("--map-center", required=True, type=str, help="The center of the map.")
    parser.add_argument("--source-id", required=True, type=str, help="The source ID of the detection results.")
    parser.add_argument("--max-obj-list-length", type=int, default=20, help="The maximum number of objects in the list. If a message is more than this number, it will be automatically split into multiple SDSM and sent to the publish topic.")
    args = parser.parse_args()
    # safely evaluate the map center from string to python tuple
    map_center = ast.literal_eval(args.map_center)
    configs = get_node_config_from_args(args)
    encoder_node = SDSMEncoderNode(
        configs,
        map_center=map_center,
        source_id=args.source_id,
        max_obj_list_length=args.max_obj_list_length
    )
    print(f"Starting the SDSM Encoder node {args.name}.")
    encoder_node.spin()

