import asyncio
import av
import cv2
import fractions
from aiortc import MediaStreamTrack
from av import VideoFrame
from ultralytics import YOLO
import logging
import platform

class VideoStreamTrack(MediaStreamTrack):
    kind = "video"
    
    def __init__(self, device_id=None, camera_id=1):  # Changed default to camera 1
        super().__init__()
        self.device_id = device_id
        self.camera_id = camera_id
        self.pts = 0
        self.system = platform.system()
        
        try:
            if self.system == "Windows":
                self.cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
            else:  # macOS or Linux
                self.cap = cv2.VideoCapture(camera_id)
            
            if not self.cap.isOpened():
                raise RuntimeError(f"Could not open camera {camera_id}")
            
            # Configure camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            # Verify if settings were applied
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            logging.info(f"Camera initialized: {camera_id}")
            logging.info(f"Resolution: {actual_width}x{actual_height}")
            logging.info(f"FPS: {actual_fps}")
            
        except Exception as e:
            logging.error(f"Error initializing camera {camera_id}: {str(e)}")
            raise RuntimeError(f"Could not initialize camera {camera_id}: {str(e)}")

        self.model = YOLO("yolov8n-face.pt")
        logging.info("YOLO face detection model loaded successfully")
        
    async def connect_to_camera(self):
        if self.device_id:
            try:
                from vrae.models import Device
                device = await Device.get(self.device_id)
                if device and device.protocol == 'RTSP':
                    # Formatação da URL RTSP com encoding da senha
                    from urllib.parse import quote
                    password = quote(device.password)  # Codifica a senha para URL
                    url = f"rtsp://{device.username}:{password}@{device.ip}:554"
                    
                    logging.info(f"Tentando conectar à câmera RTSP (encoded): {url}")
                    
                    self.cap = cv2.VideoCapture(url)
                    
                    if self.cap.isOpened():
                        logging.info("Conexão RTSP estabelecida com sucesso")
                        # Configurações para streaming RTSP
                        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        self.cap.set(cv2.CAP_PROP_FPS, 30)
                        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
                    else:
                        logging.error(f"Falha ao abrir conexão RTSP: {url}")
                else:
                    logging.info("Usando câmera padrão (fallback)")
                    self.cap = cv2.VideoCapture(0)
                    
            except Exception as e:
                logging.error(f"Erro ao conectar à câmera: {str(e)}")
                self.cap = cv2.VideoCapture(0)
        else:
            self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
            raise ConnectionError("Could not open video device")
    
    async def recv(self):
        if self.cap is None:
            await self.connect_to_camera()
            
        try:
            ret, frame = self.cap.read()
            if not ret:
                logging.error(f"Failed to capture frame from camera {self.camera_id}")
                raise RuntimeError("Failed to capture frame")

            # YOLO detection - usando modelo padrão
            results = self.model(frame, verbose=False)
            
            # Desenha as detecções
            frame = results[0].plot()
            
            # Converte BGR para RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Cria VideoFrame
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts = self.pts
            video_frame.time_base = fractions.Fraction(1, 30)
            
            self.pts += 1
            return video_frame
            
        except Exception as e:
            logging.error(f"Error in recv: {e}")
            raise
            
    def stop(self):
        if self.cap:
            self.cap.release()
        super().stop()
        
    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()