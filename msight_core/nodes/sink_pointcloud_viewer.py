from .base import SinkNode, NodeConfig
from ..data import PointCloudData
import numpy as np
import open3d as o3d

def color_by_intensity(points_struct):
    # points_struct["intensity"] is float32; normalize to [0,1] robustly
    inten = points_struct["intensity"].astype(np.float32)
    if inten.size == 0:
        return np.zeros((0,3), dtype=np.float32)
    lo, hi = np.percentile(inten, [1, 99])  # robust range
    if hi <= lo:
        hi = lo + 1.0
    norm = np.clip((inten - lo) / (hi - lo), 0.0, 1.0)
    # grayscale
    return np.stack([norm, norm, norm], axis=1).astype(np.float32)

def color_by_ring(points_struct, max_ring=None):
    ring = points_struct["ring"].astype(np.float32)
    if ring.size == 0:
        return np.zeros((0,3), dtype=np.float32)
    if max_ring is None:
        max_ring = float(np.max(ring) if ring.size else 1.0)
    max_ring = max(max_ring, 1.0)
    norm = ring / max_ring
    # simple colormap: blue->cyan->green->yellow
    return np.stack([norm, 1.0 - np.abs(norm - 0.5)*2.0, 1.0 - norm], axis=1).astype(np.float32)

class PointCloudViewerSinkNode(SinkNode):
    def __init__(self, configs, filter_sensor_name=None, voxel_downsample=None, color_mode="ring"):
        super().__init__(configs)
        self.filter_sensor_name = filter_sensor_name
        # initialize visualizer
        vis = o3d.visualization.Visualizer()
        vis.create_window(window_name=self.name, width=1280, height=800)
        opt = vis.get_render_option()
        opt.background_color = np.array([0, 0, 0], dtype=np.float32)
        opt.point_size = 1.0

        # Create geometry once; just update it each scan
        pcd = o3d.geometry.PointCloud()
        axis = o3d.geometry.TriangleMesh.create_coordinate_frame(size=1.0)
        vis.add_geometry(axis)
        vis.add_geometry(pcd)
        
        self.vis = vis
        self.opt = opt
        self.pcd = pcd
        self.axis = axis
        self.voxel_downsample = voxel_downsample
        assert color_mode in ["ring", "intensity"], "color_mode must be 'ring' or 'intensity'"
        self.color_mode = color_mode
        self.init_view_flag = False
        
        

    def on_message(self, data):
        self.logger.info(f"Received point cloud data from {data.sensor_name}")
        if self.filter_sensor_name is not None and data.sensor_name != self.filter_sensor_name:
            return
        pts = data.points
        # print(pts)
        xyz = np.column_stack([pts["x"], pts["y"], pts["z"]]).astype(np.float32)
        # self.logger.info(xyz.shape)
        if self.voxel_downsample is not None and xyz.shape[0] > 0:
            # Using Open3D voxel downsample requires a PointCloud; cheaper: random keep if huge
            # print("---------------------------------------")
            keep = 1
            if xyz.shape[0] > 500_000 and self.voxel_downsample is None:
                keep = max(1, xyz.shape[0] // 500_000)
            if keep > 1:
                xyz = xyz[::keep]
                # If downsampling, also decimate colors later accordingly

        # Colors
        if self.color_mode == "ring":
            colors = color_by_ring(pts)
        else:
            colors = color_by_intensity(pts)

            # If decimated xyz, decimate colors the same way
        if xyz.shape[0] != colors.shape[0]:
            factor = colors.shape[0] // max(1, xyz.shape[0])
            colors = colors[::max(1, factor)]

        # Update geometry
        self.pcd.points = o3d.utility.Vector3dVector(xyz)
        self.pcd.colors = o3d.utility.Vector3dVector(colors)

        ## Initialize view
        if not self.init_view_flag:
            self.vis.get_view_control().set_front([0, -1, 0])
            self.vis.get_view_control().set_up([0, 0, 1])
            self.vis.get_view_control().set_zoom(0.25)
            self.vis.reset_view_point(True)
            self.init_view_flag = True

        self.vis.update_geometry(self.pcd)
        self.vis.poll_events()
        self.vis.update_renderer()

    @classmethod
    def create(cls, name, subscribe_topic, filter_sensor_name=None, voxel_downsample=None, color_mode="ring"):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic,
            subscribe_topic_data_type=PointCloudData
        )
        return cls(
            configs=configs,
            filter_sensor_name=filter_sensor_name,
            voxel_downsample=voxel_downsample,
            color_mode=color_mode
        )

