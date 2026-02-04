import pytest
from msight_core.nodes import LocalImageSourceNode
# from msight_core.nodes.base import NodeRegisteredError
from msight_core import Topic, ImageData

topic = Topic("test_node_register", ImageData)


def test_local_image_source_node():
    node1 = LocalImageSourceNode(
        "test_node_register",
        topic,
        "test_node_register",
        "not_a_valid_path.jpg",
        10,
    )

    assert node1.name == "test_node_register"
    assert node1.publish_topic.name == "test_node_register"

    node1.unregister()
    redis_client = node1.redis_client
    # check if node is unregistered successfully
    assert not redis_client.hexists("msight_core:NODES", node1.name)



