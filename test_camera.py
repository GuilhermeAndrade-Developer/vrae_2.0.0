import cv2
import numpy as np
import time

def test_camera():
    print("Teste de câmera iniciando...")
    
    # List available cameras
    cameras = []
    for i in range(10):  # Check first 10 indexes
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # Add cv2.CAP_DSHOW for Windows
        if cap.isOpened():
            # Get camera properties
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            print(f"Câmera {i} encontrada:")
            print(f"- Resolução: {width}x{height}")
            print(f"- FPS: {fps}")
            
            cameras.append(i)
            cap.release()
    
    print(f"\nTotal de câmeras encontradas: {len(cameras)}")
    
    # Test each camera found
    for cam_id in cameras:
        print(f"\nTestando câmera {cam_id}")
        cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
        
        # Set properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Enable autofocus if available
        cap.set(cv2.CAP_PROP_BRIGHTNESS, 128)  # Set middle brightness
        
        # Wait for camera to initialize
        time.sleep(2)
        
        # Try to capture frame
        ret, frame = cap.read()
        if ret:
            print(f"Frame capturado: Shape={frame.shape}, Mean={frame.mean():.2f}")
            filename = f'test_camera_{cam_id}.jpg'
            cv2.imwrite(filename, frame)
            print(f"Frame salvo como '{filename}'")
            
            if frame.mean() < 1:
                print("AVISO: Frame está preto - possível problema de acesso à câmera")
        else:
            print(f"ERRO: Não foi possível capturar frame da câmera {cam_id}")
        
        cap.release()
    
    print("\nTeste finalizado")

if __name__ == "__main__":
    test_camera()