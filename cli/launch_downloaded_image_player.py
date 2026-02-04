from msight_core.utils import get_default_arg_parser, get_node_config_from_args
from msight_core.nodes import DownloadedImagePlayerSourceNode



def main():
    parser = get_default_arg_parser(description='play downloaded images', node_class=DownloadedImagePlayerSourceNode)

    parser.add_argument("-n", "--name", default="downloaded_image_player", help="the name of the node")
    parser.add_argument("--primary-sensor", default=None, help="the primary sensor to play")
    parser.add_argument("--fps", default=10, type=int, help="the fps of the player")
    parser.add_argument("--time-mode", default='local', help="the time mode of the player")
    args = parser.parse_args()
    assert args.time_mode in ['local', 'current'], "time mode should be either 'local' or 'current'"
    configs = get_node_config_from_args(args)
    source = DownloadedImagePlayerSourceNode(configs, args.dir, primary_sensor=args.primary_sensor, fps=args.fps, time_mode=args.time_mode)
    source.spin()

if __name__ == '__main__':
    main()



