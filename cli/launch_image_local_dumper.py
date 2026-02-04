from msight_edge.nodes import ImageLocalDumperSinkNode
from msight_edge.utils import get_default_arg_parser, get_node_config_from_args

def main():
    argparser = get_default_arg_parser(description="Launch Image Local Dumper Sink Node, this node saves image data to local folder.", node_class=ImageLocalDumperSinkNode)
    argparser.add_argument("--output-folder-path", required=True, help="Output folder path to save image data")
    
    args = argparser.parse_args()
    configs = get_node_config_from_args(args)
    image_local_dumper_sink = ImageLocalDumperSinkNode(
        configs,
        args.output_folder_path, 
   )
    image_local_dumper_sink.spin()
if __name__ == "__main__":
    main()
