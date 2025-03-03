import cv2
import numpy as np

def test_camera():
    print("Teste de câmera iniciando...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("ERRO: Não foi possível abrir a câmera")
        return
        
    ret, frame = cap.read()
    if ret:
        print(f"Frame capturado com sucesso! Dimensões: {frame.shape}")
        # Salvar frame para teste
        cv2.imwrite('test_frame.jpg', frame)
        print("Frame salvo como 'test_frame.jpg'")
    else:
        print("ERRO: Não foi possível capturar frame")
    
    cap.release()
    print("Teste finalizado")

if __name__ == "__main__":
    test_camera()