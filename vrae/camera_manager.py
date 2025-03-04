import cv2
import logging
from urllib.parse import urlparse, quote
import urllib.parse
import asyncio

class CameraManager:
    def __init__(self):
        self._cameras = {}
        logging.info("Initializing CameraManager")

    async def connect_camera(self, camera_info):
        try:
            if isinstance(camera_info, str):
                # If camera_info is a string, treat it as device_id and fetch from DB
                from .models import Device
                device = await Device.get_device(camera_info)
                if not device:
                    raise ValueError(f"No device found with id {camera_info}")
                camera_info = device

            # Get RTSP URL from camera info
            rtsp_url = camera_info.get('rtsp_url')
            if not rtsp_url:
                # Build RTSP URL if not provided
                username = quote(camera_info.get('username', ''))
                password = quote(camera_info.get('password', ''))
                ip = camera_info.get('ip', '')
                stream_path = camera_info.get('stream_path', '')
                rtsp_url = f"rtsp://{username}:{password}@{ip}:554{stream_path}"

            logging.debug(f"Attempting to connect to RTSP URL: {rtsp_url}")
            
            # Set OpenCV options for RTSP
            cap = cv2.VideoCapture(rtsp_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)  # Minimize buffer size
            
            if not cap.isOpened():
                raise RuntimeError(f"Could not open camera connection: {rtsp_url}")
            
            # Test reading a frame
            ret, frame = cap.read()
            if not ret or frame is None:
                raise RuntimeError("Could not read frame from camera")
            
            logging.info(f"Successfully connected to camera at {camera_info.get('ip')}")
            logging.debug(f"Frame shape: {frame.shape}")
            
            return cap

        except Exception as e:
            logging.error(f"Error connecting to camera: {str(e)}")
            raise RuntimeError(f"Could not initialize camera: {str(e)}")

    async def get_frame(self, cap):
        try:
            if not cap or not cap.isOpened():
                raise RuntimeError("Camera is not initialized")
                
            ret, frame = cap.read()
            if not ret or frame is None:
                raise RuntimeError("Could not read frame from camera")
                
            return frame
        except Exception as e:
            logging.error(f"Error getting frame: {str(e)}")
            raise

    @staticmethod
    async def test_connection(protocol, ip, username=None, password=None):
        """Test camera connection and get model information"""
        try:
            # Construct camera URL based on protocol
            if protocol == 'RTSP':
                if username and password:
                    url = f"rtsp://{username}:{password}@{ip}"
                else:
                    url = f"rtsp://{ip}"
            else:
                # Add other protocols as needed
                raise ValueError(f"Protocol {protocol} not supported")

            # Try to connect to camera
            cap = cv2.VideoCapture(url)
            if not cap.isOpened():
                raise ConnectionError("Could not connect to camera")

            # Try to get camera model through OpenCV properties
            model = None
            try:
                # Some cameras expose model info through v4l2 (Linux) or PROP_BACKEND_SPECIFIC
                model = cap.get(cv2.CAP_PROP_BACKEND) 
                if not model:
                    # If model not available, try to get it from ONVIF
                    # This is a placeholder - implement ONVIF discovery if needed
                    pass
            except:
                model = "Unknown"

            cap.release()
            return True, model

        except Exception as e:
            logging.error(f"Camera connection error: {str(e)}")
            return False, None