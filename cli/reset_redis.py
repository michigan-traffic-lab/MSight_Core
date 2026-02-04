import redis
import argparse
from msight_core.utils import get_redis_client


def main():
    parser = argparse.ArgumentParser(description="Reset the redis database.")
    parser.add_argument(
        "--host", type=str, default="localhost", help="The host of the redis server."
    )
    parser.add_argument(
        "-p", "--port", type=int, default="6379", help="The port of the redis server."
    )
    parser.add_argument(
        "-d", "--db", type=int, default=0, help="The db of the redis server."
    )
    args = parser.parse_args()

    redis_client = get_redis_client()
    # Pattern for keys to be deleted
    pattern = "MSIGHT*"
    for key in redis_client.scan_iter(pattern):
        redis_client.delete(key)
    print(f"Deleted all keys with pattern {pattern}.")


if __name__ == "__main__":
    main()

