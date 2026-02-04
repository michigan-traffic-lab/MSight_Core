import json
from tabulate import tabulate
from datetime import datetime

from msight_core.utils import get_redis_client
from msight_core.nodes import REDIS_NODES_FIELD
from msight_core.topics import REDIS_TOPICS_FIELD

def print_nodes(nodes):
    print("--------------------------NODES--------------------------")
    table_data = []
    for node_name, details_json in nodes.items():
        details = json.loads(details_json)
        last_heartbeat_dt = datetime.fromtimestamp(details["last_heartbeat"]).strftime('%Y-%m-%d %H:%M:%S')
        table_data.append([node_name, details["publish_topic"], details["subscribe_topic"], details["type"], last_heartbeat_dt, details["status"]])

    # Define the table headers
    headers = ["Node Name", "Publish Topic", "Subscribe Topic", "Type", "Last Heartbeat", "Status"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def print_topics(topics):
    table_data = []
    for topic_name, details_json in topics.items():
        details = json.loads(details_json)
        table_data.append([topic_name, details["data_type"], details.get("description", "")])

    # Define the table headers
    headers = ["Topic Name", "Data Type", "Description"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
def main():
    r = get_redis_client()
    # get the whole hash map of nodes
    nodes = r.hgetall(REDIS_NODES_FIELD)
    print_nodes(nodes)
    topics = r.hgetall(REDIS_TOPICS_FIELD)
    print("--------------------------TOPICS--------------------------")
    print_topics(topics)


if __name__ == '__main__':
    main()

