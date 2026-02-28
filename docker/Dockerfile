FROM python:3.10
ARG DEBIAN_FRONTEND=noninteractive
RUN apt update && apt install git libgl1 libglib2.0-0 libxcb-xinerama0 build-essential ffmpeg libsm6 libxext6 iputils-ping -y && rm -rf /var/lib/apt/lists/*
RUN pip install -U pip opencv-python numpy boto3 pysftp schedule pyyaml geopy tqdm tabulate redis pycrate
WORKDIR /msight
RUN git clone https://github.com/michigan-traffic-lab/MSight_base.git
WORKDIR /msight/MSight_base
RUN pip install .
WORKDIR /msight
RUN git clone https://github.com/michigan-traffic-lab/pyV2XLib.git
WORKDIR /msight/pyV2XLib
RUN pip install .
ADD . /msight/MSight_Core
WORKDIR /msight/MSight_Core
RUN pip install .
WORKDIR /msight
