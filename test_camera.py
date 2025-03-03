import cv2
import numpy as np
import time

def test_camera(camera_index=1):  # Changed default to camera 1
    print(f"Teste de câmera {camera_index} iniciando...")
    
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"ERRO: Não foi possível abrir a câmera {camera_index}")
        return
    
    # Get and print camera properties
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"Propriedades da câmera:")
    print(f"- Resolução: {width}x{height}")
    print(f"- FPS: {fps}")
    
    # Set properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 128)
    
    # Wait for camera to initialize
    time.sleep(2)
    
    # Capture and save frame
    ret, frame = cap.read()
    if ret:
        print(f"Frame capturado: Shape={frame.shape}, Mean={frame.mean():.2f}")
        filename = f'test_camera_{camera_index}.jpg'
        cv2.imwrite(filename, frame)
        print(f"Frame salvo como '{filename}'")
    else:
        print(f"ERRO: Não foi possível capturar frame")
    
    cap.release()
    print("Teste finalizado")

if __name__ == "__main__":
    test_camera(1)  # Use camera 1 explicitly