import cv2
import numpy as np
import time

def test_camera():
    print("Teste de câmera iniciando...")
    
    # Listar dispositivos disponíveis
    device_count = 0
    while True:
        cap = cv2.VideoCapture(device_count)
        if not cap.isOpened():
            break
        print(f"Câmera {device_count} encontrada")
        cap.release()
        device_count += 1
    print(f"Total de câmeras encontradas: {device_count}")
    
    # Testar câmera principal
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERRO: Não foi possível abrir a câmera")
        return
    
    # Configurar propriedades da câmera
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Aguardar um pouco para a câmera inicializar
    time.sleep(2)
    
    # Tentar capturar alguns frames
    for i in range(5):
        ret, frame = cap.read()
        if ret:
            print(f"Frame {i} capturado: Shape={frame.shape}, Mean={frame.mean()}")
            if frame.mean() < 1:
                print("AVISO: Frame parece estar escuro/preto")
            cv2.imwrite(f'test_frame_{i}.jpg', frame)
            print(f"Frame salvo como 'test_frame_{i}.jpg'")
        else:
            print(f"ERRO: Falha ao capturar frame {i}")
        time.sleep(0.5)
    
    cap.release()
    print("Teste finalizado")

if __name__ == "__main__":
    test_camera()