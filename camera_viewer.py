import cv2
import json
import os
import time
from datetime import datetime

def load_camera_config(ip):
    """Load camera configuration from saved JSON file"""
    config_file = os.path.join('config', f'camera_{ip.replace(".", "_")}.json')
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"No configuration found for camera {ip}")
    
    with open(config_file, 'r') as f:
        return json.load(f)

def view_camera(config, quality='high'):
    """Display camera stream using OpenCV"""
    url = config['profiles'][quality]
    print(f"\nConnecting to camera stream ({quality} quality)...")
    print(f"URL: {url}")
    
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        raise ConnectionError("Failed to open RTSP stream")
    
    # Set buffer size and timeout
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    window_name = f"Camera Stream ({quality})"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    fps = 0
    frame_count = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame")
            break
        
        # Calculate FPS
        frame_count += 1
        if frame_count % 30 == 0:
            end_time = time.time()
            fps = 30 / (end_time - start_time)
            start_time = time.time()
        
        # Add overlay with information
        height, width = frame.shape[:2]
        overlay = frame.copy()
        
        # Add text
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_color = (255, 255, 255)
        bg_color = (0, 0, 0)
        
        info_text = [
            f"Resolution: {width}x{height}",
            f"FPS: {fps:.1f}",
            f"Quality: {quality}",
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        ]
        
        y = 30
        for text in info_text:
            # Add background rectangle
            text_size = cv2.getTextSize(text, font, 0.7, 2)[0]
            cv2.rectangle(overlay, (10, y-20), (text_size[0]+20, y+5), bg_color, -1)
            # Add text
            cv2.putText(overlay, text, (15, y), font, 0.7, text_color, 2)
            y += 30
        
        # Blend overlay with original frame
        alpha = 0.7
        cv2.addWeighted(overlay, alpha, frame, 1-alpha, 0, frame)
        
        cv2.imshow(window_name, frame)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):  # Quit
            break
        elif key == ord('h'):  # High quality
            quality = 'high'
            cap.release()
            cap = cv2.VideoCapture(config['profiles']['high'])
        elif key == ord('m'):  # Medium quality
            quality = 'medium'
            cap.release()
            cap = cv2.VideoCapture(config['profiles']['medium'])
        elif key == ord('l'):  # Low quality
            quality = 'low'
            cap.release()
            cap = cv2.VideoCapture(config['profiles']['low'])
        elif key == ord('s'):  # Save snapshot
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"snapshot_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            print(f"Snapshot saved: {filename}")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    ip = "192.168.100.18"
    try:
        config = load_camera_config(ip)
        print("\nCamera Viewer")
        print("Controls:")
        print("  q - Quit")
        print("  h - High quality")
        print("  m - Medium quality")
        print("  l - Low quality")
        print("  s - Save snapshot")
        view_camera(config)
    except Exception as e:
        print(f"Error: {str(e)}")