import argparse
import boto3
from pathlib import Path
import re
import pytz
from datetime import datetime
from tqdm import tqdm
# import base64
import json
from msight_core.utils import dynamic_import
from msight_core.data import ImageData

def uncompile(x: Path, output_path: Path):
    output_path.mkdir(parents=True, exist_ok=True)
    with open(x, 'r') as f:
        while True:
            l = f.readline()
            if not l:
                break
            payload = json.loads(l)
            data_type = dynamic_import(payload['data_type'])
            # print(data_type)
            data = data_type.from_json(l)
            t = data.time
            #print(f"processing image of time {t}")
            # jpg_original = base64.b64decode(payload['image'])
            if type(data) == ImageData:
                jpg_original = data.encoded_image
            t = t.replace(':', '-').replace('.', '-')
            if hasattr(data, 'detection_results') and data.detection_results is not None:
                detection_results = data.detection_results
                detection_results_json = detection_results.to_json()
                with open(f'{output_path/t}.json', 'w') as f_output:
                    f_output.write(detection_results_json)
            # Write to a file to show conversion worked
            with open(f'{output_path/t}.jpg', 'wb') as f_output:
                f_output.write(jpg_original)



def rm_dir(pth: Path):
    for child in pth.glob('*'):
        if child.is_file():
            child.unlink()
        else:
            rm_dir(child)
    pth.rmdir()


def save_sensor_data(
    s3_client,
    bucket,
    device,
    sensor_name,
    date_str,
    hr_str,
    yyyy,
    mm,
    dd,
    hh,
    output_path,
    match_pattern
):
    prefix = f"{device}/{sensor_name}/{date_str}/{hr_str}"
    print(f"downloading data from s3://{bucket}/{prefix}...")
    objs = s3_client.list_objects(Bucket=bucket, Prefix=prefix)
    if "Contents" not in objs:
        print(f"no data found for {prefix}")
        return
    sensor_download_path = output_path / f"{yyyy}-{mm}-{dd}" / f"{hh}" / f"{device}_{sensor_name}"
    sensor_download_path.mkdir(parents=True, exist_ok=True)
    raw_download_path = sensor_download_path / "tmp"
    raw_download_path.mkdir(parents=True, exist_ok=True)
    for obj in tqdm(objs["Contents"]):
        if match_pattern is not None:
            # when match_pattern is passed in, we check if pattern matches before downloading
            m = re.search(match_pattern, obj['Key'])
            if m is None:
                continue
        key = obj["Key"]
        if key.endswith("/"):
            continue
        file_name = key.split("/")[-1]
        file_path = raw_download_path / file_name
        s3_client.download_file(bucket, key, str(file_path))
        uncompile(file_path, sensor_download_path)
    rm_dir(raw_download_path)


def main():
    parser = argparse.ArgumentParser(description="download from S3")
    parser.add_argument("-b", "--bucket", required=True)
    parser.add_argument("--device", required=True, help="device name")
    parser.add_argument(
        "-s",
        "--sensors",
        nargs="+",
        help="list of sensors",
        required=True,
    )
    parser.add_argument(
        "-d",
        "--date",
        required=True,
        help="the date of data you want to download, format is yyyy-mm-dd, use Eastern time",
    )
    parser.add_argument(
        "--hours",
        nargs="+",
        required=True,
        help="the hour of the date you want to download",
    )
    parser.add_argument(
        "--dir", help="directory path to download", type=Path, default="./output"
    )
    parser.add_argument(
        "--match-pattern",
        help="file key match pattern in regular expression",
        default=None,
    )
    args = parser.parse_args()
    # TZ_UTC = pytz.timezone('UTC')  # UTC timezone
    TZ_LOCAL = pytz.timezone("America/New_York")  # eastern time timezone
    s3_client = boto3.client("s3")
    bucket = args.bucket
    device = args.device
    date_matched = re.match(r"(\d{4})\-(\d{2})\-(\d{2})", args.date)
    assert date_matched is not None, "--date must be in format of yyyy-mm-dd"
    yyyy, mm, dd = date_matched.groups()
    for hh in args.hours:
        for sensor_name in args.sensors:
            # operate timezone:
            t_est = datetime.strptime(
                f"{yyyy}-{mm}-{dd} {hh}:00:00", "%Y-%m-%d %H:%M:%S"
            )
            t_est = TZ_LOCAL.localize(t_est)
            # convert eastern time to UTC
            t_utc = t_est.astimezone(pytz.timezone("utc"))
            date_str = t_utc.strftime("%Y-%m-%d")
            hr_str = str(t_utc.hour).zfill(2)
            print(f"downloading sensor data for hour {hh}, sensor {sensor_name}...")
            save_sensor_data(
                s3_client,
                bucket,
                device,
                sensor_name,
                date_str,
                hr_str,
                yyyy,
                mm,
                dd,
                hh,
                args.dir,
                args.match_pattern,
            )

