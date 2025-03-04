import asyncio
import av
import cv2
import fractions
from aiortc import MediaStreamTrack
from av import VideoFrame
from ultralytics import YOLO
import logging
import platform
from .camera_manager import CameraManager
from .models import Device
import subprocess
import time
from aiortc.mediastreams import AUDIO_PTIME, MediaStreamError
from fractions import Fraction
import numpy as np

class VideoStreamTrack(MediaStreamTrack):
    kind = "video"
    
    def __init__(self, device_id=None):
        super().__init__()
        self.device_id = device_id
        self.cap = None
        self._running = True
        self._frame_rate = 30
        self._width = 1920  # Full HD
        self._height = 1080
        self._timestamp = 0
        self._time_base = fractions.Fraction(1, 90000)
        logging.info(f"Initializing HD VideoStreamTrack for device {device_id}")

    async def connect_to_camera(self):
        try:
            from .models import Device
            device = await Device.get_device(self.device_id)
            if not device:
                raise ValueError(f"No device found with id {self.device_id}")

            rtsp_url = device.get('rtsp_url')
            logging.info(f"Connecting to camera at: {rtsp_url}")

            # Configure OpenCV with optimal settings
            self.cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            
            # Set camera properties with double values
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2.0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(self._width))
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self._height))
            self.cap.set(cv2.CAP_PROP_FPS, float(self._frame_rate))
            self.cap.set(cv2.CAP_PROP_CONVERT_RGB, 0.0)  # Fixed: Use 0.0 instead of False
            
            # Configure H264 codec
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))

            if not self.cap.isOpened():
                raise RuntimeError(f"Could not open RTSP stream")

            # Test frame reading
            ret, frame = self.cap.read()
            if not ret or frame is None:
                raise RuntimeError("Could not read frame from camera")

            logging.info(f"Successfully connected to camera {self.device_id}")
            logging.debug(f"Frame shape: {frame.shape}")
            return True

        except Exception as e:
            logging.error(f"Error connecting to camera: {str(e)}")
            if self.cap:
                self.cap.release()
            raise

    async def recv(self):
        if not self._running:
            raise MediaStreamError("Track ended")

        try:
            if not self.cap or not self.cap.isOpened():
                await self.connect_to_camera()

            ret, frame = self.cap.read()
            if not ret:
                raise RuntimeError("Could not read frame")

            # Enhance image quality
            frame = cv2.resize(frame, (self._width, self._height), 
                             interpolation=cv2.INTER_LANCZOS4)

            # Improve sharpness
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            frame = cv2.filter2D(frame, -1, kernel)

            # Adjust contrast and brightness
            frame = cv2.convertScaleAbs(frame, alpha=1.1, beta=5)

            # Convert BGR to RGB with high quality
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Create VideoFrame with optimal settings
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            pts = self._timestamp
            self._timestamp += int(90000 / self._frame_rate)
            video_frame.pts = pts
            video_frame.time_base = self._time_base

            return video_frame

        except Exception as e:
            logging.error(f"Error in recv: {str(e)}")
            if self.cap and self.cap.isOpened():
                self.cap.release()
            raise

    def stop(self):
        self._running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        super().stop()
        
    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()