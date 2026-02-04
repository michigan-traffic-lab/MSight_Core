from msight_core.data import BytesData

def test_bytes_data():
    b = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09'
    bytes_data = BytesData(sensor_name="test_sensor", data=b)
    assert bytes_data.data == b
    assert bytes_data.sensor_name == "test_sensor"
    bytes_data_serialized = bytes_data.serialize()
    bytes_data_deserialized = BytesData.deserialize(bytes_data_serialized)
    assert bytes_data_deserialized.sensor_name == "test_sensor"
    assert bytes_data_deserialized.data == b

