import numpy as np
import matplotlib.pyplot as plt
import cv2
import os

import torch

from torchvision import transforms, utils

import json

import re
import datetime

import pickle

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")



def create_folder(folder_dir):
    if os.path.exists(folder_dir) is False:
        os.mkdir(folder_dir)

def save_detection(vehicle_list, traj_output_folder, basename):
    out_path = os.path.join(traj_output_folder, basename.replace('.jpg', '.pickle'))
    pickle.dump(vehicle_list, open(out_path, "wb"))

def make_coords(x_steps, y_steps, x1=0, x2=1, y1=0, y2=1):

    # Create input pixel coordinates in the unit square
    x_coords = np.linspace(x1, x2, x_steps, endpoint=True, dtype=np.float32)
    y_coords = np.linspace(y1, y2, y_steps, endpoint=True, dtype=np.float32)
    x_coords_2d, y_coords_2d = np.meshgrid(x_coords, y_coords)

    return x_coords_2d, y_coords_2d


def make_numpy_grid(tensor_data):
    tensor_data = tensor_data.detach()
    vis = utils.make_grid(tensor_data)
    vis = np.array(vis.cpu()).transpose((1,2,0))
    if vis.shape[2] == 1:
        vis = np.stack([vis, vis, vis], axis=-1)
    return vis


class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)

def parse_config(path_to_json=r'./config.json'):

    with open(path_to_json) as f:
      data = json.load(f)
    args = Struct(**data)

    return args



def cpt_pxl_cls_acc(pred_idx, target):
    pred_idx = torch.reshape(pred_idx, [-1])
    target = torch.reshape(target, [-1])
    return torch.mean((pred_idx.int()==target.int()).float())


def cpt_batch_psnr(img, img_gt, PIXEL_MAX):
    mse = torch.mean((img - img_gt) ** 2, dim=[1,2,3])
    psnr = 20 * torch.log10(PIXEL_MAX / torch.sqrt(mse))
    return torch.mean(psnr)


def cpt_psnr(img, img_gt, PIXEL_MAX):
    mse = np.mean((img - img_gt) ** 2)
    psnr = 20 * np.log10(PIXEL_MAX / np.sqrt(mse))
    return psnr



def bb_intersection_over_union(boxA, boxB):

    # determine the (x, y)-coordinates of the intersection rectangle
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    # compute the area of intersection rectangle
    interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
    # compute the area of both the prediction and ground-truth
    # rectangles
    boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
    boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
    # compute the intersection over union by taking the intersection
    # area and dividing it by the sum of prediction + ground-truth
    # areas - the interesection area
    iou = interArea / float(boxAArea + boxBArea - interArea)

    # return the intersection over union value
    return iou


def remove_overlapped_bbs(vehicle_list):

    rmv_ids = [False]*len(vehicle_list)

    for i in range(len(vehicle_list)):
        if rmv_ids[i]:
            continue
        for j in range(i+1, len(vehicle_list)):
            vi, vj = vehicle_list[i], vehicle_list[j]
            bbi = vi.pixel_bb
            bbj = vj.pixel_bb
            iou = bb_intersection_over_union(bbi, bbj)
            if iou > 0.5:
                rmv_ids[j] = True

    vehicle_list_final = []
    for i in range(len(vehicle_list)):
        if not rmv_ids[i]:
            vehicle_list_final.append(vehicle_list[i])

    return vehicle_list_final

def _vehicle_list_to_labelme(vehicle_list, img_h, img_w, filename):

    data = {}
    data['version'] = '4.5.7'
    data['flags'] = {}
    data['imagePath'] = filename + '.jpg'
    data['imageData'] = None
    data['imageHeight'] = img_h
    data['imageWidth'] = img_w

    shapes = []
    for i in range(len(vehicle_list)):
        v = vehicle_list[i]
        obj = {}
        obj['label'] = None
        obj['group_id'] = None
        obj['shape_type'] = 'rectangle'
        obj['flags'] = {}
        x1, y1, x2, y2 = v.pixel_bb
        obj['points'] = [[x1, y1], [x2, y2]]
        shapes.append(obj)

    data['shapes'] = shapes

    return data


def save_labelme_annotation(vehicle_list, img, out_folder, filename):

    img_h, img_w = img.shape[0:2]
    data = _vehicle_list_to_labelme(vehicle_list, img_h=img_h, img_w=img_w, filename=filename)

    # save labelme json
    out_path = os.path.join(out_folder, filename+'.json')
    with open(out_path, 'w') as f:
        json.dump(data, f)

    # save img data
    out_path = os.path.join(out_folder, filename+'.jpg')
    cv2.imwrite(out_path, img)


class VideoWriter(object):

    def __init__(self, name, out_size_w=960, out_size_h=720):

        self.video_writer = cv2.VideoWriter(
            name + '.mp4', cv2.VideoWriter_fourcc(*'MP4V'),
            10.0, (out_size_w, out_size_h))
        self.video_writer_cat = cv2.VideoWriter(
            name + '_cat.mp4', cv2.VideoWriter_fourcc(*'MP4V'),
            10.0, (out_size_h + out_size_w, out_size_h))

        self.out_size_w = out_size_w
        self.out_size_h = out_size_h

    def save_frame(self, vis_det, vis_loc, display=True):

        vis_det = cv2.resize(vis_det, (self.out_size_w, self.out_size_h))
        vis_loc = cv2.resize(vis_loc, (self.out_size_h, self.out_size_h))

        self.video_writer.write(vis_det[:, :, ::-1])

        frame_cat = np.concatenate([vis_det, vis_loc], axis=1)
        self.video_writer_cat.write(frame_cat[:, :, ::-1])

        if display:
            cv2.namedWindow('frame_cat', cv2.WINDOW_NORMAL)
            cv2.imshow('frame_cat', frame_cat[:, :, ::-1])
        cv2.waitKey(1)



class SynchImgParser(object):

    def __init__(self, img_dir_ne, img_dir_nw, img_dir_se, img_dir_sw, warp_matrices=None):

        self.img_dir_ne = img_dir_ne
        self.img_dir_nw = img_dir_nw
        self.img_dir_se = img_dir_se
        self.img_dir_sw = img_dir_sw
        self.timestamp_ne = np.array(list(map(self.filename2timestamp, img_dir_ne)))
        self.timestamp_nw = np.array(list(map(self.filename2timestamp, img_dir_nw)))
        self.timestamp_se = np.array(list(map(self.filename2timestamp, img_dir_se)))
        self.timestamp_sw = np.array(list(map(self.filename2timestamp, img_dir_sw)))
        self.timestamps = {
            'gs_ne_corner': self.timestamp_ne,
            'gs_nw_corner': self.timestamp_nw,
            'gs_se_corner': self.timestamp_se,
            'gs_sw_corner': self.timestamp_sw,
        }
        self.dirs = {
            'gs_ne_corner': self.img_dir_ne,
            'gs_nw_corner': self.img_dir_nw,
            'gs_se_corner': self.img_dir_se,
            'gs_sw_corner': self.img_dir_sw
        }
        self.warp_matrices = warp_matrices

    def __len__(self):
        return len(self.img_dir_ne)

    def filename2timestamp(self, filename):
        f = re.split('\-|\s', os.path.splitext(os.path.basename(filename))[0])
        t = datetime.datetime(*map(int, f))
        t = datetime.datetime.timestamp(t)
        return t

    def pull_images(self, image_name):

        timestamp_query = self.filename2timestamp(image_name)

        idx_ne = np.argmin(np.abs(self.timestamp_ne - timestamp_query))
        idx_nw = np.argmin(np.abs(self.timestamp_nw - timestamp_query))
        idx_se = np.argmin(np.abs(self.timestamp_se - timestamp_query))
        idx_sw = np.argmin(np.abs(self.timestamp_sw - timestamp_query))

        img_ne = cv2.imread(self.img_dir_ne[idx_ne], cv2.IMREAD_COLOR)
        img_nw = cv2.imread(self.img_dir_nw[idx_nw], cv2.IMREAD_COLOR)
        img_se = cv2.imread(self.img_dir_se[idx_se], cv2.IMREAD_COLOR)
        img_sw = cv2.imread(self.img_dir_sw[idx_sw], cv2.IMREAD_COLOR)

        img_ne = cv2.cvtColor(img_ne, cv2.COLOR_BGR2RGB)
        img_nw = cv2.cvtColor(img_nw, cv2.COLOR_BGR2RGB)
        img_se = cv2.cvtColor(img_se, cv2.COLOR_BGR2RGB)
        img_sw = cv2.cvtColor(img_sw, cv2.COLOR_BGR2RGB)

        IMG_BUFF = {'gs_ne_corner': img_ne, 'gs_nw_corner': img_nw,
                    'gs_se_corner': img_se, 'gs_sw_corner': img_sw}
        
        file_names = {'gs_ne_corner': self.img_dir_ne[idx_ne], 'gs_nw_corner': self.img_dir_nw[idx_nw],
                      'gs_se_corner': self.img_dir_se[idx_se], 'gs_sw_corner': self.img_dir_sw[idx_sw]}

        return IMG_BUFF, file_names

    def pull_images_with_alignment(self, image_name):

        timestamp_query = self.filename2timestamp(image_name)

        idx_ne = np.argmin(np.abs(self.timestamp_ne - timestamp_query))
        idx_nw = np.argmin(np.abs(self.timestamp_nw - timestamp_query))
        idx_se = np.argmin(np.abs(self.timestamp_se - timestamp_query))
        idx_sw = np.argmin(np.abs(self.timestamp_sw - timestamp_query))

        img_ne = cv2.imread(self.img_dir_ne[idx_ne], cv2.IMREAD_COLOR)
        img_nw = cv2.imread(self.img_dir_nw[idx_nw], cv2.IMREAD_COLOR)
        img_se = cv2.imread(self.img_dir_se[idx_se], cv2.IMREAD_COLOR)
        img_sw = cv2.imread(self.img_dir_sw[idx_sw], cv2.IMREAD_COLOR)

        img_ne = cv2.cvtColor(img_ne, cv2.COLOR_BGR2RGB)
        img_nw = cv2.cvtColor(img_nw, cv2.COLOR_BGR2RGB)
        img_se = cv2.cvtColor(img_se, cv2.COLOR_BGR2RGB)
        img_sw = cv2.cvtColor(img_sw, cv2.COLOR_BGR2RGB)

        # image alignment to reduce the effect of view change
        sz = img_sw.shape
        # img_sw = cv2.warpAffine(img_sw, self.warp_matrices['sw'], (sz[1],sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
        img_sw = cv2.warpPerspective(img_sw, self.warp_matrices['sw'], (sz[1],sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
        img_nw = cv2.warpPerspective(img_nw, self.warp_matrices['se'], (sz[1],sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
        img_se = cv2.warpPerspective(img_se, self.warp_matrices['nw'], (sz[1],sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
        img_ne = cv2.warpPerspective(img_ne, self.warp_matrices['ne'], (sz[1],sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)

        IMG_BUFF = {'gs_ne_corner': img_ne, 'gs_nw_corner': img_nw,
                    'gs_se_corner': img_se, 'gs_sw_corner': img_sw}
        
        file_names = {'gs_ne_corner': self.img_dir_ne[idx_ne], 'gs_nw_corner': self.img_dir_nw[idx_nw],
                      'gs_se_corner': self.img_dir_se[idx_se], 'gs_sw_corner': self.img_dir_sw[idx_sw]}

        return IMG_BUFF, file_names


class SynchImgParserV2(object):

    def __init__(self, img_dir_dict, warp_matrices=None):

        self.dirs = img_dir_dict
        # self.img_dir_nw = img_dir_nw
        # self.img_dir_se = img_dir_se
        # self.img_dir_sw = img_dir_sw
        self.timestamp = dict()
        for key in self.dirs.keys():
            self.timestamp[key] = np.array(list(map(self.filename2timestamp, self.dirs[key])))
        # self.timestamp_ne = np.array(list(map(self.filename2timestamp, img_dir_ne)))
        # self.timestamp_nw = np.array(list(map(self.filename2timestamp, img_dir_nw)))
        # self.timestamp_se = np.array(list(map(self.filename2timestamp, img_dir_se)))
        # self.timestamp_sw = np.array(list(map(self.filename2timestamp, img_dir_sw)))
        # self.timestamps = {
        #     'gs_ne_corner': self.timestamp_ne,
        #     'gs_nw_corner': self.timestamp_nw,
        #     'gs_se_corner': self.timestamp_se,
        #     'gs_sw_corner': self.timestamp_sw,
        # }
        # self.dirs = {
        #     'gs_ne_corner': self.img_dir_ne,
        #     'gs_nw_corner': self.img_dir_nw,
        #     'gs_se_corner': self.img_dir_se,
        #     'gs_sw_corner': self.img_dir_sw
        # }
        self.warp_matrices = warp_matrices

    def __len__(self):
        return len(self.dirs[list(self.dirs.keys())[0]])

    def filename2timestamp(self, filename):
        f = re.split('\-|\s', os.path.splitext(os.path.basename(filename))[0])
        t = datetime.datetime(*map(int, f))
        t = datetime.datetime.timestamp(t)
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
        # idx_ne = np.argmin(np.abs(self.timestamp_ne - timestamp_query))
        # idx_nw = np.argmin(np.abs(self.timestamp_nw - timestamp_query))
        # idx_se = np.argmin(np.abs(self.timestamp_se - timestamp_query))
        # idx_sw = np.argmin(np.abs(self.timestamp_sw - timestamp_query))

        # img_ne = cv2.imread(self.img_dir_ne[idx_ne], cv2.IMREAD_COLOR)
        # img_nw = cv2.imread(self.img_dir_nw[idx_nw], cv2.IMREAD_COLOR)
        # img_se = cv2.imread(self.img_dir_se[idx_se], cv2.IMREAD_COLOR)
        # img_sw = cv2.imread(self.img_dir_sw[idx_sw], cv2.IMREAD_COLOR)

        # img_ne = cv2.cvtColor(img_ne, cv2.COLOR_BGR2RGB)
        # img_nw = cv2.cvtColor(img_nw, cv2.COLOR_BGR2RGB)
        # img_se = cv2.cvtColor(img_se, cv2.COLOR_BGR2RGB)
        # img_sw = cv2.cvtColor(img_sw, cv2.COLOR_BGR2RGB)

        # IMG_BUFF = {'gs_ne_corner': img_ne, 'gs_nw_corner': img_nw,
        #             'gs_se_corner': img_se, 'gs_sw_corner': img_sw}
        
        # file_names = {'gs_ne_corner': self.img_dir_ne[idx_ne], 'gs_nw_corner': self.img_dir_nw[idx_nw],
        #               'gs_se_corner': self.img_dir_se[idx_se], 'gs_sw_corner': self.img_dir_sw[idx_sw]}

        return IMG_BUFF, file_names



class SynchImgParser8Way(object):

    def __init__(self, gs_dir_ne, gs_dir_nw, gs_dir_se, gs_dir_sw,
                       fl_dir_ne, fl_dir_nw, fl_dir_se, fl_dir_sw):

        self.gs_dir_ne = gs_dir_ne
        self.gs_dir_nw = gs_dir_nw
        self.gs_dir_se = gs_dir_se
        self.gs_dir_sw = gs_dir_sw
        self.timestamp_gs_ne = np.array(list(map(self.filename2timestamp, gs_dir_ne)))
        self.timestamp_gs_nw = np.array(list(map(self.filename2timestamp, gs_dir_nw)))
        self.timestamp_gs_se = np.array(list(map(self.filename2timestamp, gs_dir_se)))
        self.timestamp_gs_sw = np.array(list(map(self.filename2timestamp, gs_dir_sw)))
        self.fl_dir_ne = fl_dir_ne
        self.fl_dir_nw = fl_dir_nw
        self.fl_dir_se = fl_dir_se
        self.fl_dir_sw = fl_dir_sw
        self.timestamp_fl_ne = np.array(list(map(self.filename2timestamp, fl_dir_ne)))
        self.timestamp_fl_nw = np.array(list(map(self.filename2timestamp, fl_dir_nw)))
        self.timestamp_fl_se = np.array(list(map(self.filename2timestamp, fl_dir_se)))
        self.timestamp_fl_sw = np.array(list(map(self.filename2timestamp, fl_dir_sw)))

    def __len__(self):
        return len(self.gs_dir_ne)

    def filename2timestamp(self, filename):
        f = re.split('\-|\s', os.path.splitext(os.path.basename(filename))[0])
        t = datetime.datetime(*map(int, f))
        t = datetime.datetime.timestamp(t)
        return t

    def pull_images(self, image_name):

        timestamp_query = self.filename2timestamp(image_name)
        delta_t = 1.0

        idx_gs_ne = np.argmin(np.abs(self.timestamp_gs_ne - timestamp_query))
        idx_gs_nw = np.argmin(np.abs(self.timestamp_gs_nw - timestamp_query))
        idx_gs_se = np.argmin(np.abs(self.timestamp_gs_se - timestamp_query))
        idx_gs_sw = np.argmin(np.abs(self.timestamp_gs_sw - timestamp_query))

        img_gs_ne = cv2.imread(self.gs_dir_ne[idx_gs_ne], cv2.IMREAD_COLOR)
        img_gs_nw = cv2.imread(self.gs_dir_nw[idx_gs_nw], cv2.IMREAD_COLOR)
        img_gs_se = cv2.imread(self.gs_dir_se[idx_gs_se], cv2.IMREAD_COLOR)
        img_gs_sw = cv2.imread(self.gs_dir_sw[idx_gs_sw], cv2.IMREAD_COLOR)

        idx_fl_ne = np.argmin(np.abs(self.timestamp_fl_ne - timestamp_query + delta_t))
        idx_fl_nw = np.argmin(np.abs(self.timestamp_fl_nw - timestamp_query + delta_t))
        idx_fl_se = np.argmin(np.abs(self.timestamp_fl_se - timestamp_query + delta_t))
        idx_fl_sw = np.argmin(np.abs(self.timestamp_fl_sw - timestamp_query + delta_t))

        img_fl_ne = cv2.imread(self.fl_dir_ne[idx_fl_ne], cv2.IMREAD_COLOR)
        img_fl_nw = cv2.imread(self.fl_dir_nw[idx_fl_nw], cv2.IMREAD_COLOR)
        img_fl_se = cv2.imread(self.fl_dir_se[idx_fl_se], cv2.IMREAD_COLOR)
        img_fl_sw = cv2.imread(self.fl_dir_sw[idx_fl_sw], cv2.IMREAD_COLOR)

        IMG_BUFF_GS = {'gs_ne_corner': img_gs_ne, 'gs_nw_corner': img_gs_nw,
                    'gs_se_corner': img_gs_se, 'gs_sw_corner': img_gs_sw}
        IMG_BUFF_FL = {'fl_ne_corner': img_fl_ne, 'fl_nw_corner': img_fl_nw,
                    'fl_se_corner': img_fl_se, 'fl_sw_corner': img_fl_sw}

        print(image_name)
        print(self.fl_dir_ne[idx_fl_ne])
        print(self.fl_dir_nw[idx_fl_nw])
        print(self.fl_dir_se[idx_fl_se])
        print(self.fl_dir_sw[idx_fl_sw])
        print()

        return IMG_BUFF_GS, IMG_BUFF_FL


def get_warp_matrix_between_two_image(img1, img2, read_img2=True):

    # Read the images to be aligned
    im1 =  cv2.imread(img1)
    if read_img2:
        im2 =  cv2.imread(img2)
    else:
        im2 = img2

    # Convert images to grayscale
    im1_gray = cv2.cvtColor(im1,cv2.COLOR_BGR2GRAY)
    im2_gray = cv2.cvtColor(im2,cv2.COLOR_BGR2GRAY)

    # Find size of image1
    sz = im1.shape

    # Define the motion model
    warp_mode = cv2.MOTION_HOMOGRAPHY

    # Define 2x3 or 3x3 matrices and initialize the matrix to identity
    if warp_mode == cv2.MOTION_HOMOGRAPHY :
        warp_matrix = np.eye(3, 3, dtype=np.float32)
    else :
        warp_matrix = np.eye(2, 3, dtype=np.float32)

    # Specify the number of iterations.
    number_of_iterations = 50

    # Specify the threshold of the increment
    # in the correlation coefficient between two iterations
    termination_eps = 1e-10

    # Define termination criteria
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, number_of_iterations,  termination_eps)

    # Run the ECC algorithm. The results are stored in warp_matrix.
    (cc, warp_matrix) = cv2.findTransformECC (im1_gray,im2_gray,warp_matrix, warp_mode, criteria)
    return warp_matrix