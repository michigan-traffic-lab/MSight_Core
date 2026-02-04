from .base import DataProcessingNode, NodeConfig
from ..data import RoadUserListData, BytesData
from pyv2xlib.SDSMEncoder import sdsm_encoder
from datetime import datetime

from geopy import distance as geodistance
from datetime import datetime
import numpy as np
NAN = 10000000000

'''
0: car
1: truck
2: bus
3: trailer
4: motorbike/cycler
5: pedestrian
6: van
7: pickup
'''

OBJ_CLASS_MAPPING = {
    -1: 'unknown',
    0: 'vehicle',
    1: 'vehicle',
    2: 'vehicle',
    3: 'vehicle',
    4: 'VRU',
    5: 'VRU',
    6: 'vehicle',
    7: 'vehicle',
    8: 'vehicle',
    9: 'vehicle',
}

def dydx_distance(lat1, lon1, lat2, lon2):
    # dx, dy = (lat2 - lat1) * 111000., (lon2 - lon1) * 111000. * np.cos(lat2/180*np.pi)
    dx = geodistance.geodesic([lat2, lon1], [lat1, lon1]).m * np.sign(lat2 - lat1)
    dy = geodistance.geodesic([lat2, lon2], [lat2, lon1]).m * np.sign(lon2 - lon1)
    return dx, dy

def get_offsetx(v, center):
    # real value with meter unit
    return dydx_distance(center[0], center[1], v.x, v.y)[0]

def get_offsety(v, center):
    return dydx_distance(center[0], center[1], v.x, v.y)[1]

# definition of posConfidence
# positionConfidence ::= ENUMERATED {
#       unavailable (0),  -- B'0000  Not
#       a500m   (1), -- B'0001  500m
#       a200m   (2), -- B'0010  200m
#       a100m   (3), -- B'0011  100m
#       a50m    (4), -- B'0100  50m
#       a20m    (5), -- B'0101  20m
#       a10m    (6), -- B'0110  10m
#       a5m     (7), -- B'0111  5m
#       a2m     (8), -- B'1000  2m
#       a1m     (9), -- B'1001  1m
#       a50cm  (10), -- B'1010  0.50m
#       a20cm  (11), -- B'1011  0.20m
#       a10cm  (12), -- B'1100  0.10m
#       a5cm   (13), -- B'1101  0.05m
#       a2cm   (14), -- B'1110  0.02m
#       a1cm   (15)  -- B'1111  0.01m
#       }
def get_posConfidence(v, raw=False):
    if v.conf_int_2sigma is None or v.conf_int_2sigma < 0:
        return 0
    pos_confidence_interval = np.sqrt(2) * v.conf_int_2sigma
    if raw:
        return pos_confidence_interval
    if pos_confidence_interval > 500:
        return 1
    elif pos_confidence_interval > 200:
        return 2
    elif pos_confidence_interval > 100:
        return 3
    elif pos_confidence_interval > 50:
        return 4
    elif pos_confidence_interval > 20:
        return 5
    elif pos_confidence_interval > 10:
        return 6
    elif pos_confidence_interval > 5:
        return 7
    elif pos_confidence_interval > 2:
        return 8
    elif pos_confidence_interval > 1:
        return 9
    elif pos_confidence_interval > 0.5:
        return 10
    elif pos_confidence_interval > 0.2:
        return 11
    elif pos_confidence_interval > 0.1:
        return 12
    elif pos_confidence_interval > 0.05:
        return 13
    elif pos_confidence_interval > 0.02:
        return 14
    elif pos_confidence_interval > 0:
        return 15
    else:
        return 0


def get_speed(v, raw=False):
    if v.speed is not None:
        if np.isnan(v.speed) or v.speed < 0:
            return NAN 
        elif raw:
            return v.speed
        return v.speed * 50
    else:
        return NAN

def get_speedconfidence(v, raw=False):
    if v.conf_int_vel_2sigma is None or v.conf_int_vel_2sigma < 0:
        return 0
    speed_confidence_interval = np.sqrt(2) * v.conf_int_vel_2sigma
    if raw:
        return speed_confidence_interval
    if speed_confidence_interval > 100:
        return 1
    elif speed_confidence_interval > 10:
        return 2
    elif speed_confidence_interval > 5:
        return 3
    elif speed_confidence_interval > 1:
        return 4
    elif speed_confidence_interval > 0.1:
        return 5
    elif speed_confidence_interval > 0.05:
        return 6
    elif speed_confidence_interval > 0:
        return 7
    else:
        return 0
     
def get_heading(v):
    if v.heading is not None:
        # move heading to the interval of [0, 360] then  return
        heading = int(v.heading) % 360
        return heading
    else:
        return NAN

def get_headingconfidence(v):
    if v.heading_confidence is not None:
        return int(v.heading_confidence) % 360
    else:
        return NAN

def get_yaw_rate(v):
    if v.yaw_rate is not None:
        return v.yaw_rate
    else:
        return NAN

# class SDSMEncoder:

def encode_sdsm(name, vehicle_list, map_center, msgCnt=1, timestamp:float=None):
    # get current day and time
    if timestamp is not None:
        now = datetime.fromtimestamp(timestamp)
    else:
        now = datetime.now()
    # compute dayOfMonth, hour, minute, second based on the current day and time
    # month = now.month
    # dayOfMonth = now.day
    # hour = now.hour
    # minute = now.minute
    # second = now.second + now.microsecond / 1000000

    # center lat, lon from basemap
    # center = [42.3009215, -83.698659]
    center = map_center
    # msgCnt=1
    # convert name to bytes
    sourceID=name
    equipmentType='rsu'
    objects_N=len(vehicle_list)
    sDSMTimeStamp_year = now.year
    sDSMTimeStamp_month = now.month
    sDSMTimeStamp_day=now.day
    sDSMTimeStamp_hour=now.hour
    sDSMTimeStamp_minute=now.minute
    sDSMTimeStamp_second=now.second + now.microsecond / 1000000
    sDSMTimeStamp_offset=0
    refPos_lat=center[0]
    refPos_long=center[1]
    refPos_elevation=0
    refPosXYConf_semiMajor=12.7
    refPosXYConf_semiMinor=12.7
    refPosXYConf_orientation=0
    refPosElConf=0

    objects_detObjCommon_objType=[OBJ_CLASS_MAPPING[int(v.category)] if v.category is not None else 'unknown' for v in vehicle_list] # 0: unknown, 1: vehicle, 2: VRU, 3: animal
    objects_detObjCommon_objTypeCfd=[int(v.confidence*100) for v in vehicle_list]
    objects_detObjCommon_objectID=[int(v.traj_id)%65535 for v in vehicle_list]
    objects_detObjCommon_measurementTime=[-1 for v in vehicle_list]
    objects_detObjCommon_timeConfidence=[NAN for v in vehicle_list]
    objects_detObjCommon_pos_offsetX=[get_offsetx(v, center) for v in vehicle_list]
    objects_detObjCommon_pos_offsetY=[get_offsety(v, center) for v in vehicle_list]
    objects_detObjCommon_pos_offsetZ=[0 for v in vehicle_list]
    objects_detObjCommon_posConfidence_pos=[get_posConfidence(v, raw=True) for v in vehicle_list]
    objects_detObjCommon_posConfidence_elevation=[0 for v in vehicle_list]
    objects_detObjCommon_speed=[get_speed(v, raw=True) for v in vehicle_list]
    objects_detObjCommon_speedConfidence=[get_speedconfidence(v, raw=True) for v in vehicle_list]
    objects_detObjCommon_speedZ=[NAN for v in vehicle_list]
    objects_detObjCommon_speedConfidenceZ=[0 for v in vehicle_list]
    objects_detObjCommon_heading=[get_heading(v) for v in vehicle_list]
    objects_detObjCommon_headingConf=[get_headingconfidence(v) for v in vehicle_list]
    objects_detObjCommon_accel4way_lat=[NAN for v in vehicle_list]
    objects_detObjCommon_accel4way_long=[NAN for v in vehicle_list]
    objects_detObjCommon_accel4way_vert=[NAN for v in vehicle_list]
    objects_detObjCommon_accel4way_yaw=[get_yaw_rate(v) for v in vehicle_list]
    objects_detObjCommon_accCfdX=[0 for v in vehicle_list]
    objects_detObjCommon_accCfdY=[0 for v in vehicle_list]
    objects_detObjCommon_accCfdZ=[0 for v in vehicle_list]
    objects_detObjCommon_accCfdYaw=[0 for v in vehicle_list]

    # print all the values for debugging
    # print(f'encoding {objects_N} objects, sourceID={sourceID}, equipmentType={equipmentType}, msgCnt={msgCnt}')
    # print(f'sDSMTimeStamp_year={sDSMTimeStamp_year}, sDSMTimeStamp_month={sDSMTimeStamp_month}, sDSMTimeStamp_day={sDSMTimeStamp_day}, sDSMTimeStamp_hour={sDSMTimeStamp_hour}, sDSMTimeStamp_minute={sDSMTimeStamp_minute}, sDSMTimeStamp_second={sDSMTimeStamp_second}, sDSMTimeStamp_offset={sDSMTimeStamp_offset}')
    # print(f'refPos_lat={refPos_lat}, refPos_long={refPos_long}, refPos_elevation={refPos_elevation}, refPosXYConf_semiMajor={refPosXYConf_semiMajor}, refPosXYConf_semiMinor={refPosXYConf_semiMinor}, refPosXYConf_orientation={refPosXYConf_orientation}, refPosElConf={refPosElConf}')
    # print(f'objects_detObjCommon_objType={objects_detObjCommon_objType}')
    # print(f'objects_detObjCommon_objTypeCfd={objects_detObjCommon_objTypeCfd}')
    # print(f'objects_detObjCommon_objectID={objects_detObjCommon_objectID}')
    # print(f'objects_detObjCommon_measurementTime={objects_detObjCommon_measurementTime}')
    # print(f'objects_detObjCommon_timeConfidence={objects_detObjCommon_timeConfidence}')
    # print(f'objects_detObjCommon_pos_offsetX={objects_detObjCommon_pos_offsetX}')
    # print(f'objects_detObjCommon_pos_offsetY={objects_detObjCommon_pos_offsetY}')
    # print(f'objects_detObjCommon_pos_offsetZ={objects_detObjCommon_pos_offsetZ}')
    # print(f'objects_detObjCommon_posConfidence_pos={objects_detObjCommon_posConfidence_pos}')
    # print(f'objects_detObjCommon_posConfidence_elevation={objects_detObjCommon_posConfidence_elevation}')
    # print(f'objects_detObjCommon_speed={objects_detObjCommon_speed}')
    # print(f'objects_detObjCommon_speedConfidence={objects_detObjCommon_speedConfidence}')
    # print(f'objects_detObjCommon_speedZ={objects_detObjCommon_speedZ}')
    # print(f'objects_detObjCommon_speedConfidenceZ={objects_detObjCommon_speedConfidenceZ}')
    # print(f'objects_detObjCommon_heading={objects_detObjCommon_heading}')
    # print(f'objects_detObjCommon_headingConf={objects_detObjCommon_headingConf}')
    # print(f'objects_detObjCommon_accel4way_lat={objects_detObjCommon_accel4way_lat}')
    # print(f'objects_detObjCommon_accel4way_long={objects_detObjCommon_accel4way_long}')
    # print(f'objects_detObjCommon_accel4way_vert={objects_detObjCommon_accel4way_vert}')
    # print(f'objects_detObjCommon_accel4way_yaw={objects_detObjCommon_accel4way_yaw}')
    # print(f'objects_detObjCommon_accCfdX={objects_detObjCommon_accCfdX}')
    # print(f'objects_detObjCommon_accCfdY={objects_detObjCommon_accCfdY}')
    # print(f'objects_detObjCommon_accCfdZ={objects_detObjCommon_accCfdZ}')
    # print(f'objects_detObjCommon_accCfdYaw={objects_detObjCommon_accCfdYaw}')

    encode_info = {
        "msgCnt": msgCnt,
        "sourceID": sourceID,
        "equipmentType": equipmentType,
        "objects_N": objects_N,
        "sDSMTimeStamp_year": sDSMTimeStamp_year,
        "sDSMTimeStamp_month": sDSMTimeStamp_month,
        "sDSMTimeStamp_day": sDSMTimeStamp_day,
        "sDSMTimeStamp_hour": sDSMTimeStamp_hour,
        "sDSMTimeStamp_minute": sDSMTimeStamp_minute,
        "sDSMTimeStamp_second": sDSMTimeStamp_second,
        "sDSMTimeStamp_offset": sDSMTimeStamp_offset,
        "refPos_lat": refPos_lat,
        "refPos_long": refPos_long,
        "refPos_elevation": refPos_elevation,
        "refPosXYConf_semiMajor": refPosXYConf_semiMajor,
        "refPosXYConf_semiMinor": refPosXYConf_semiMinor,
        "refPosXYConf_orientation": refPosXYConf_orientation,
        "refPosElConf": refPosElConf,
        "objects_detObjCommon_objType": objects_detObjCommon_objType,
        "objects_detObjCommon_objTypeCfd": objects_detObjCommon_objTypeCfd,
        "objects_detObjCommon_objectID": objects_detObjCommon_objectID,
        "objects_detObjCommon_measurementTime": objects_detObjCommon_measurementTime,
        "objects_detObjCommon_timeConfidence": objects_detObjCommon_timeConfidence,
        "objects_detObjCommon_pos_offsetX": objects_detObjCommon_pos_offsetX,
        "objects_detObjCommon_pos_offsetY": objects_detObjCommon_pos_offsetY,
        "objects_detObjCommon_pos_offsetZ": objects_detObjCommon_pos_offsetZ,
        "objects_detObjCommon_posConfidence_pos": objects_detObjCommon_posConfidence_pos,
        "objects_detObjCommon_posConfidence_elevation": objects_detObjCommon_posConfidence_elevation,
        "objects_detObjCommon_speed": objects_detObjCommon_speed,
        "objects_detObjCommon_speedConfidence": objects_detObjCommon_speedConfidence,
        "objects_detObjCommon_speedZ": objects_detObjCommon_speedZ,
        "objects_detObjCommon_speedConfidenceZ": objects_detObjCommon_speedConfidenceZ,
        "objects_detObjCommon_heading": objects_detObjCommon_heading,
        "objects_detObjCommon_headingConf": objects_detObjCommon_headingConf,
        "objects_detObjCommon_accel4way_lat": objects_detObjCommon_accel4way_lat,
        "objects_detObjCommon_accel4way_long": objects_detObjCommon_accel4way_long,
        "objects_detObjCommon_accel4way_vert": objects_detObjCommon_accel4way_vert,
        "objects_detObjCommon_accel4way_yaw": objects_detObjCommon_accel4way_yaw,
        "objects_detObjCommon_accCfdX": objects_detObjCommon_accCfdX,
        "objects_detObjCommon_accCfdY": objects_detObjCommon_accCfdY,
        "objects_detObjCommon_accCfdZ": objects_detObjCommon_accCfdZ,
        "objects_detObjCommon_accCfdYaw": objects_detObjCommon_accCfdYaw,
    }
    
    return sdsm_encoder(
        msgCnt=msgCnt,
        sourceID=sourceID,
        equipmentType=equipmentType,
        objects_N=objects_N,
        sDSMTimeStamp_year=sDSMTimeStamp_year,
        sDSMTimeStamp_month=sDSMTimeStamp_month,
        sDSMTimeStamp_day=sDSMTimeStamp_day,
        sDSMTimeStamp_hour=sDSMTimeStamp_hour,
        sDSMTimeStamp_minute=sDSMTimeStamp_minute,
        sDSMTimeStamp_second=sDSMTimeStamp_second,
        sDSMTimeStamp_offset=sDSMTimeStamp_offset,
        refPos_lat=refPos_lat,
        refPos_long=refPos_long,
        # refPos_elevation=refPos_elevation,
        refPosXYConf_semiMajor=refPosXYConf_semiMajor,
        refPosXYConf_semiMinor=refPosXYConf_semiMinor,
        refPosXYConf_orientation=refPosXYConf_orientation,
        # refPosElConf=refPosElConf,
        objects_detObjCommon_objType=objects_detObjCommon_objType,
        objects_detObjCommon_objTypeCfd=objects_detObjCommon_objTypeCfd,
        objects_detObjCommon_objectID=objects_detObjCommon_objectID,
        objects_detObjCommon_measurementTime=objects_detObjCommon_measurementTime,
        objects_detObjCommon_timeConfidence=objects_detObjCommon_timeConfidence,
        objects_detObjCommon_pos_offsetX=objects_detObjCommon_pos_offsetX,
        objects_detObjCommon_pos_offsetY=objects_detObjCommon_pos_offsetY,
        # objects_detObjCommon_pos_offsetZ=objects_detObjCommon_pos_offsetZ,
        objects_detObjCommon_posConfidence_pos=objects_detObjCommon_posConfidence_pos,
        objects_detObjCommon_posConfidence_elevation=objects_detObjCommon_posConfidence_elevation,
        objects_detObjCommon_speed=objects_detObjCommon_speed,
        objects_detObjCommon_speedConfidence=objects_detObjCommon_speedConfidence,
        # objects_detObjCommon_speedZ=objects_detObjCommon_speedZ,
        # objects_detObjCommon_speedConfidenceZ=objects_detObjCommon_speedConfidenceZ,
        objects_detObjCommon_heading=objects_detObjCommon_heading,
        objects_detObjCommon_headingConf=objects_detObjCommon_headingConf,
        # objects_detObjCommon_accel4way_lat=objects_detObjCommon_accel4way_lat,
        # objects_detObjCommon_accel4way_long=objects_detObjCommon_accel4way_long,
        # objects_detObjCommon_accel4way_vert=objects_detObjCommon_accel4way_vert,
        # objects_detObjCommon_accel4way_yaw=objects_detObjCommon_accel4way_yaw,
        # objects_detObjCommon_accCfdX=objects_detObjCommon_accCfdX,
        # objects_detObjCommon_accCfdY=objects_detObjCommon_accCfdY,
        # objects_detObjCommon_accCfdZ=objects_detObjCommon_accCfdZ,
        # objects_detObjCommon_accCfdYaw=objects_detObjCommon_accCfdYaw,
    ), encode_info


class SDSMEncoderNode(DataProcessingNode):
    default_configs = NodeConfig(
        heartbeat_tolerance=-1,
        publish_topic_data_type=BytesData,
    )
    def __init__(self, configs, map_center, source_id, max_obj_list_length=20, ):
        super().__init__(configs)
        self.msgCnt = 0
        self.map_center = map_center
        self.source_id = source_id
        self.max_obj_list_length = max_obj_list_length
        # self.equipmentType = self.configs["equipmentType"]

    def process(self, data: RoadUserListData):
        self.logger.info(f"Received data of size {len(data.road_user_list)}.")
        assert isinstance(data, RoadUserListData), "Data must be RoadUserListData"
        #timestring = data.time
        timestamp = data.capture_timestamp
        if len(data.road_user_list) == 0:
            return None

        # split the original road user list into sub lists
        sub_lists = [data.road_user_list[i:i + 20] for i in range(0, len(data.road_user_list), 20)]
        self.msgCnt += 1
        if self.msgCnt > 127:
            self.msgCnt = 0
        # try:
        data_list = []
        for road_user_list in sub_lists:
            # print(road_user_list)
            hex_data, encode_info = encode_sdsm(self.source_id, road_user_list, self.map_center, msgCnt=self.msgCnt, timestamp=timestamp)
            # except Exception as e:
            #     self.logger.error(f"Failed to encode SDSM data: {e}")
            #     return None
            # convert hex to bytes
            self.logger.debug(f"Encoded SDSM data: {encode_info}")
            raw_bytes_data = bytes.fromhex(hex_data)
            bytes_data = BytesData(data=raw_bytes_data, capture_timestamp=data.capture_timestamp, sensor_name=data.sensor_name)
            data_list.append(bytes_data)
        self.logger.info(f"Encoded {len(data_list)} SDSM messages with msgCnt={self.msgCnt}. Total number of objects: {len(data.road_user_list)}.")
        return data_list
    
    @classmethod
    def create(cls, name, subscribe_topic, publish_topic, map_center, source_id, max_obj_list_length=20):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic,
            publish_topic_name=publish_topic,
            # equipmentType=equipmentType,
        )
        return cls(configs, map_center, source_id, max_obj_list_length=max_obj_list_length) 

