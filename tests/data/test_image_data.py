import pytest
from msight_core.data import ImageData
import cv2
import logging
from pathlib import Path

def test_image_data():
    logging.info('start testing image data ...')
    image_path = Path(__file__).parent / "sample_image.jpg"
    image = cv2.imread(str(image_path))
    image_data = ImageData.from_ndarray(image, "test_sensor", is_encoded=True)
    # print(len(image_data.image))
    image_data_bytes = image_data.serialize()
    # print(len(image_data_bytes))
    image_data_deserialized = ImageData.deserialize(image_data_bytes)
    img = image_data_deserialized.to_ndarray()
    img_size = img.shape[:2]
    assert img_size[0] == image_data_deserialized.size[0] and img_size[1] == image_data_deserialized.size[1], f"Image size mismatch after deserialization: expected {image_data_deserialized.size}, got {img_size}"
    assert image_data_deserialized.sensor_name == "test_sensor", "Sensor name mismatch after deserialization"
    # print(type(image_data_deserialized))

    ## test non-encoded
    image_data = ImageData.from_ndarray(image, "test_sensor", is_encoded=False)
    image_data_bytes = image_data.serialize()
    image_data_deserialized = ImageData.deserialize(image_data_bytes)
    img = image_data_deserialized.to_ndarray()
    img_size = img.shape[:2]
    assert img_size[0] == image_data_deserialized.size[0] and img_size[1] == image_data_deserialized.size[1], f"Image size mismatch after deserialization: expected {image_data_deserialized.size}, got {img_size}"
    assert image_data_deserialized.sensor_name == "test_sensor", "Sensor name mismatch after deserialization"
    assert image_data_deserialized.is_encoded == False, "is_encoded should be False for non-encoded image data"
    # print(type(image_data_deserialized))
    # cv2.imshow('test', img)
    # cv2.waitKey(0)
    logging.info('image data test passed')
    # cv2.imwrite(str("test.jpg"), img)
    

