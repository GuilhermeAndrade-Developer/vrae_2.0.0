import cv2
import logging
from urllib.parse import urlparse

class CameraManager:
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