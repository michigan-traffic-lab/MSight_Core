import pytest
import numpy as np
from msight_core.data import PointCloudData

import numpy as np
from pathlib import Path

PCD_DTYPE = np.dtype([
    ("x", "<f4"),
    ("y", "<f4"),
    ("z", "<f4"),
    ("intensity", "<f4"),
    ("time", "<f4"),
    ("column", "<u2"),
    ("ring",  "|u1"),
    ("return_type", "|u1"),
])

def load_pcd_structured(path: str | Path) -> np.ndarray:
    path = Path(path)
    with path.open("rb") as f:
        # Skip header until DATA ...
        while True:
            line = f.readline()
            if not line:
                raise ValueError("Reached EOF before DATA line.")
            if line.decode("ascii", errors="ignore").strip().startswith("DATA"):
                break
        data = f.read()

    points = np.frombuffer(data, dtype=PCD_DTYPE)
    return points


def test_pointcloud_data():
    pc_path = "./sample_point_cloud.pcd"
    pts_struct = load_pcd_structured(pc_path)

    point_cloud_data = PointCloudData.from_ndarray(
        points=pts_struct,
        sensor_name="test_sensor",
    )

    point_cloud_data_bytes = point_cloud_data.serialize()
    point_cloud_data_deserialized = PointCloudData.deserialize(point_cloud_data_bytes)
    pts_deserialized = point_cloud_data_deserialized.points

    assert point_cloud_data_deserialized.sensor_name == "test_sensor"
    assert pts_struct.dtype == pts_deserialized.dtype, "Point cloud dtype mismatch after deserialization"
    assert np.array_equal(pts_struct, pts_deserialized), "Point cloud data mismatch after deserialization"
