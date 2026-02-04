import pytest
from msight_edge.utils import convert_msight_det_object_list_to_detection_result, convert_detection_result_to_msight_det_object_list
from msight_edge.data import DetectionResultsData
import time
from datetime import datetime
import glob
from msight_det import YOLOV8Detector as Detector, Fusion, Localizer, Tracker, StateEstimator
import time
import os
from pathlib import Path
import cv2
import numpy as np
import re

class SynchImgParserV2(object):

    def __init__(self, img_dir_dict, warp_matrices=None):

        self.dirs = img_dir_dict
        # self.img_dir_nw = img_dir_nw
        # self.img_dir_se = img_dir_se
        # self.img_dir_sw = img_dir_sw
        self.timestamp = dict()
        for key in self.dirs.keys():
            self.timestamp[key] = np.array(list(map(self.filename2timestamp, self.dirs[key])))

        self.warp_matrices = warp_matrices

    def __len__(self):
        return len(self.dirs[list(self.dirs.keys())[0]])

    def filename2timestamp(self, filename):
        f = re.split('\-|\s', os.path.splitext(os.path.basename(filename))[0])
        t = datetime(*map(int, f))
        t = datetime.timestamp(t)
        return t

    def pull_images(self, image_name):

        timestamp_query = self.filename2timestamp(image_name)
        IMG_BUFF = dict()
        file_names = dict()

        for key in self.dirs.keys():
            idx = np.argmin(np.abs(self.timestamp[key] - timestamp_query))
            img = cv2.imread(self.dirs[key][idx], cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            if self.warp_matrices is not None:
                sz = img.shape
                img = cv2.warpPerspective(img, self.warp_matrices[key], (sz[1],sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
            IMG_BUFF[key] = img
            file_names[key] = self.dirs[key][idx]

        return IMG_BUFF, file_names





def test_detection_result_data():
        
    FRAME_RATE = 10
    current_path = Path(__file__).parent

   

    LOC_MAPS = {'mcity_edge2-gs-ne': str(current_path / 'loc_maps/locmap_sip_gs_ne_2023_v1.npz'),
                'mcity_edge2-gs-sw': str(current_path / 'loc_maps/locmap_sip_gs_sw_2023_v1.npz')}    
    
    img_dir_ne= sorted(glob.glob(os.path.join(
        str(current_path / 'mcity' / 'mcity_edge-gs-ne'), '*.jpg')))
    img_dir_sw= sorted(glob.glob(os.path.join(
        str(current_path / 'mcity' / 'mcity_edge-gs-sw'), '*.jpg')))


    synch_img_parser = SynchImgParserV2({'mcity_edge2-gs-ne': img_dir_ne,
                                        'mcity_edge2-gs-sw': img_dir_sw})

    # initialize detector
    
    det = Detector(ckpt=str(current_path / 'checkpoints/yolov8m_midadvrb_pretrained_mcitygs.pt'), in_size_w=640, in_size_h=640, model_size='nano',
                    std_imgs=None, async_align=False, confthre=0.2, nmsthre=0.5)

    localizer = Localizer(loc_maps=LOC_MAPS)
    fusion = Fusion(mode='mcity_gs')
    tracker = Tracker()
    state_estimator = StateEstimator(frame_rate=FRAME_RATE)


    # BASE_MAP_CENTER = eval("[42.300941929800096, -83.69865020358655]")


    for i in range(len(synch_img_parser)):
        # load image buffer
        # begin_load_image = time.time()
        # t_beg = time.time()
        IMG_BUFF, filenames = synch_img_parser.pull_images(img_dir_ne[i])

        # begin_det = time.time()
        # detection and localization
        VEHICLE_BUFF = det.detect(IMG_BUFF)

        detection_result_gs_ne = VEHICLE_BUFF['mcity_edge2-gs-ne']
        detection_result_gs_ne_data = convert_msight_det_object_list_to_detection_result(detection_result_gs_ne, str(datetime.now()), "mcity_edge2-gs-ne", time.time())
        assert detection_result_gs_ne_data.sensor_name == "mcity_edge2-gs-ne"
        assert detection_result_gs_ne_data.time is not None
        assert detection_result_gs_ne_data.event_timestamp is not None
        assert detection_result_gs_ne_data.detection_object_list is not None
        deserializaed_detection_result_gs_ne_data = DetectionResultsData.deserialize(detection_result_gs_ne_data.serialize())
        assert deserializaed_detection_result_gs_ne_data.sensor_name == "mcity_edge2-gs-ne"
        assert deserializaed_detection_result_gs_ne_data.time == detection_result_gs_ne_data.time
        assert deserializaed_detection_result_gs_ne_data.event_timestamp == detection_result_gs_ne_data.event_timestamp
        assert deserializaed_detection_result_gs_ne_data.detection_object_list is not None
        assert len(deserializaed_detection_result_gs_ne_data.detection_object_list) == len(detection_result_gs_ne)


        for j in range(len(deserializaed_detection_result_gs_ne_data.detection_object_list)):
            assert deserializaed_detection_result_gs_ne_data.detection_object_list[j]['id'] == detection_result_gs_ne[j].id
            assert deserializaed_detection_result_gs_ne_data.detection_object_list[j]['confidence'] == detection_result_gs_ne[j].confidence
            assert deserializaed_detection_result_gs_ne_data.detection_object_list[j]['category'] == detection_result_gs_ne[j].category


            

        detection_result_gs_sw = VEHICLE_BUFF['mcity_edge2-gs-sw']
        detection_result_gs_sw_data = convert_msight_det_object_list_to_detection_result(detection_result_gs_sw, str(datetime.now()), "mcity_edge2-gs-sw", time.time())
        assert detection_result_gs_sw_data.sensor_name == "mcity_edge2-gs-sw"
        assert detection_result_gs_sw_data.time is not None
        assert detection_result_gs_sw_data.event_timestamp is not None
        assert detection_result_gs_sw_data.detection_object_list is not None
        deserializaed_detection_result_gs_sw_data = DetectionResultsData.deserialize(detection_result_gs_sw_data.serialize())
        assert deserializaed_detection_result_gs_sw_data.sensor_name == "mcity_edge2-gs-sw"
        assert deserializaed_detection_result_gs_sw_data.time == detection_result_gs_sw_data.time
        assert deserializaed_detection_result_gs_sw_data.event_timestamp == detection_result_gs_sw_data.event_timestamp
        assert deserializaed_detection_result_gs_sw_data.detection_object_list is not None
        assert len(deserializaed_detection_result_gs_sw_data.detection_object_list) == len(detection_result_gs_sw)
        for j in range(len(deserializaed_detection_result_gs_sw_data.detection_object_list)):
            assert deserializaed_detection_result_gs_sw_data.detection_object_list[j]['id'] == detection_result_gs_sw[j].id
            assert deserializaed_detection_result_gs_sw_data.detection_object_list[j]['confidence'] == detection_result_gs_sw[j].confidence
            assert deserializaed_detection_result_gs_sw_data.detection_object_list[j]['category'] == detection_result_gs_sw[j].category

        
        new_v_buff = {
            "mcity_edge2-gs-ne": convert_detection_result_to_msight_det_object_list(deserializaed_detection_result_gs_ne_data),
            "mcity_edge2-gs-sw": convert_detection_result_to_msight_det_object_list(deserializaed_detection_result_gs_sw_data)
        }

        # localization
        VEHICLE_BUFF = localizer.localize(new_v_buff)

        localization_result_gs_ne = VEHICLE_BUFF['mcity_edge2-gs-ne']
        localization_result_gs_ne_data = convert_msight_det_object_list_to_detection_result(localization_result_gs_ne, str(datetime.now()), "mcity_edge2-gs-ne", time.time())
        assert localization_result_gs_ne_data.sensor_name == "mcity_edge2-gs-ne"
        assert localization_result_gs_ne_data.time is not None
        assert localization_result_gs_ne_data.event_timestamp is not None
        assert localization_result_gs_ne_data.detection_object_list is not None
        deserializaed_localization_result_gs_ne_data = DetectionResultsData.deserialize(localization_result_gs_ne_data.serialize())
        assert deserializaed_localization_result_gs_ne_data.sensor_name == "mcity_edge2-gs-ne"
        assert deserializaed_localization_result_gs_ne_data.time == localization_result_gs_ne_data.time
        assert deserializaed_localization_result_gs_ne_data.event_timestamp == localization_result_gs_ne_data.event_timestamp
        assert deserializaed_localization_result_gs_ne_data.detection_object_list is not None
        assert len(deserializaed_localization_result_gs_ne_data.detection_object_list) == len(localization_result_gs_ne)


        for j in range(len(deserializaed_localization_result_gs_ne_data.detection_object_list)):
            assert deserializaed_localization_result_gs_ne_data.detection_object_list[j]['id'] == localization_result_gs_ne[j].id
            assert deserializaed_localization_result_gs_ne_data.detection_object_list[j]['confidence'] == localization_result_gs_ne[j].confidence
            assert deserializaed_localization_result_gs_ne_data.detection_object_list[j]['category'] == localization_result_gs_ne[j].category


            

        localization_result_gs_sw = VEHICLE_BUFF['mcity_edge2-gs-sw']
        localization_result_gs_sw_data = convert_msight_det_object_list_to_detection_result(localization_result_gs_sw, str(datetime.now()), "mcity_edge2-gs-sw", time.time())
        assert localization_result_gs_sw_data.sensor_name == "mcity_edge2-gs-sw"
        assert localization_result_gs_sw_data.time is not None
        assert localization_result_gs_sw_data.event_timestamp is not None
        assert localization_result_gs_sw_data.detection_object_list is not None
        deserializaed_localization_result_gs_sw_data = DetectionResultsData.deserialize(localization_result_gs_sw_data.serialize())
        assert deserializaed_localization_result_gs_sw_data.sensor_name == "mcity_edge2-gs-sw"
        assert deserializaed_localization_result_gs_sw_data.time == localization_result_gs_sw_data.time
        assert deserializaed_localization_result_gs_sw_data.event_timestamp == localization_result_gs_sw_data.event_timestamp
        assert deserializaed_localization_result_gs_sw_data.detection_object_list is not None
        assert len(deserializaed_localization_result_gs_sw_data.detection_object_list) == len(localization_result_gs_sw)
        for j in range(len(deserializaed_localization_result_gs_sw_data.detection_object_list)):
            assert deserializaed_localization_result_gs_sw_data.detection_object_list[j]['id'] == localization_result_gs_sw[j].id
            assert deserializaed_localization_result_gs_sw_data.detection_object_list[j]['confidence'] == localization_result_gs_sw[j].confidence
            assert deserializaed_localization_result_gs_sw_data.detection_object_list[j]['category'] == localization_result_gs_sw[j].category


        new_v_buff = {
            "mcity_edge2-gs-ne": convert_detection_result_to_msight_det_object_list(deserializaed_localization_result_gs_ne_data),
            "mcity_edge2-gs-sw": convert_detection_result_to_msight_det_object_list(deserializaed_localization_result_gs_sw_data)
        }




        # fusion
        VEHICLE_BUFF['fusion'] = fusion.fuse_detection(VEHICLE_BUFF)

        fusion_result = VEHICLE_BUFF['fusion'] 
        fusion_result_data = convert_msight_det_object_list_to_detection_result(fusion_result, str(datetime.now()), "mcity_edge2-fusion", time.time())
        assert fusion_result_data.sensor_name == "mcity_edge2-fusion"
        assert fusion_result_data.time is not None
        assert fusion_result_data.event_timestamp is not None
        assert fusion_result_data.detection_object_list is not None
        deserializaed_fusion_result_data = DetectionResultsData.deserialize(fusion_result_data.serialize())
        assert deserializaed_fusion_result_data.sensor_name == "mcity_edge2-fusion"
        assert deserializaed_fusion_result_data.time == fusion_result_data.time
        assert deserializaed_fusion_result_data.event_timestamp == fusion_result_data.event_timestamp
        assert deserializaed_fusion_result_data.detection_object_list is not None
        assert len(deserializaed_fusion_result_data.detection_object_list) == len(fusion_result)


        for j in range(len(deserializaed_fusion_result_data.detection_object_list)):
            assert deserializaed_fusion_result_data.detection_object_list[j]['id'] == fusion_result[j].id
            assert deserializaed_fusion_result_data.detection_object_list[j]['confidence'] == fusion_result[j].confidence
            assert deserializaed_fusion_result_data.detection_object_list[j]['category'] == fusion_result[j].category




        # tracking
        VEHICLE_BUFF['fusion'] = tracker.track(VEHICLE_BUFF['fusion'])
        tracking_result = VEHICLE_BUFF['fusion'] 
        tracking_result_data = convert_msight_det_object_list_to_detection_result(tracking_result, str(datetime.now()), "mcity_edge2-tracking", time.time())
        assert tracking_result_data.sensor_name == "mcity_edge2-tracking"
        assert tracking_result_data.time is not None
        assert tracking_result_data.event_timestamp is not None
        assert tracking_result_data.detection_object_list is not None
        deserializaed_tracking_result_data = DetectionResultsData.deserialize(tracking_result_data.serialize())
        assert deserializaed_tracking_result_data.sensor_name == "mcity_edge2-tracking"
        assert deserializaed_tracking_result_data.time == tracking_result_data.time
        assert deserializaed_tracking_result_data.event_timestamp == tracking_result_data.event_timestamp
        assert deserializaed_tracking_result_data.detection_object_list is not None
        assert len(deserializaed_tracking_result_data.detection_object_list) == len(tracking_result)


        for j in range(len(deserializaed_tracking_result_data.detection_object_list)):
            assert deserializaed_tracking_result_data.detection_object_list[j]['id'] == tracking_result[j].id
            assert deserializaed_tracking_result_data.detection_object_list[j]['confidence'] == tracking_result[j].confidence
            assert deserializaed_tracking_result_data.detection_object_list[j]['category'] == tracking_result[j].category


        # state estimation
        VEHICLE_BUFF['fusion'] = state_estimator.estimate(VEHICLE_BUFF['fusion'])
        VEHICLE_BUFF['fusion'] = tracker.track(VEHICLE_BUFF['fusion'])
        state_estimation_result = VEHICLE_BUFF['fusion'] 
        state_estimation_result_data = convert_msight_det_object_list_to_detection_result(state_estimation_result, str(datetime.now()), "mcity_edge2-state_estimation", time.time())
        assert state_estimation_result_data.sensor_name == "mcity_edge2-state_estimation"
        assert state_estimation_result_data.time is not None
        assert state_estimation_result_data.event_timestamp is not None
        assert state_estimation_result_data.detection_object_list is not None
        deserializaed_state_estimation_result_data = DetectionResultsData.deserialize(state_estimation_result_data.serialize())
        assert deserializaed_state_estimation_result_data.sensor_name == "mcity_edge2-state_estimation"
        assert deserializaed_state_estimation_result_data.time == state_estimation_result_data.time
        assert deserializaed_state_estimation_result_data.event_timestamp == state_estimation_result_data.event_timestamp
        assert deserializaed_state_estimation_result_data.detection_object_list is not None
        assert len(deserializaed_state_estimation_result_data.detection_object_list) == len(state_estimation_result)


        for j in range(len(deserializaed_state_estimation_result_data.detection_object_list)):
            assert deserializaed_state_estimation_result_data.detection_object_list[j]['id'] == state_estimation_result[j].id
            assert deserializaed_state_estimation_result_data.detection_object_list[j]['confidence'] == state_estimation_result[j].confidence
            assert deserializaed_state_estimation_result_data.detection_object_list[j]['category'] == state_estimation_result[j].category