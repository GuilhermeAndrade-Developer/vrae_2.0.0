import cv2
from ultralytics import YOLO
from flask import Response, jsonify, stream_with_context
import logging
from .models import User
import json

MAX_RETRIES = 10


class StreamManager:
    def __init__(self, model_path='yolov8n.pt'):
        self.model = YOLO(model_path)
        self.camera = None
        self.logger = logging.getLogger(__name__)
        self.stream_active = False

    async def generate_frames(self):
        self.stream_active = True
        self.logger.info("Starting video stream")
        
        try:
            if self.camera is None:
                self.camera = cv2.VideoCapture(0)
            
            while self.stream_active:
                success, frame = self.camera.read()
                if not success:
                    break
                    
                results = self.model(frame)
                annotated_frame = results[0].plot()
                
                ret, buffer = cv2.imencode('.jpg', annotated_frame)
                if not ret:
                    continue
                    
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                       
        except Exception as e:
            self.logger.error(f"Stream error: {str(e)}")
        finally:
            self.stop_stream()

    def stop_stream(self):
        self.stream_active = False
        if self.camera is not None:
            self.camera.release()
            self.camera = None


stream_manager = StreamManager()


def get_stream_response(current_user):
    """Rota de resposta para o stream de vídeo contínuo."""
    logging.debug("Iniciando o fluxo de vídeo")

    def generate():
        try:
            for frame in stream_manager.generate_frames():
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            logging.error(f"Erro no generate: {str(e)}")
            yield b''

    response = Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
    
    response.headers.update({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'Connection': 'close'
    })
    
    return response


def get_stop_stream_response(current_user):
    """Rota para interromper o streaming de vídeo."""
    logging.debug(f"User {current_user.username} acessando /stop_streaming")
    stream_manager.stop_streaming()
    return jsonify({"message": "Streaming encerrado."}), 200
