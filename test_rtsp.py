import subprocess
import urllib.parse
import time
import socket
import requests
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
import json
import os
from datetime import datetime

def test_port(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        sock.close()
        return False

def test_web_interface(ip, username, password):
    """Test HTTP/HTTPS access to camera web interface and try to find RTSP URL"""
    urls = [
        f"http://{ip}",
        f"https://{ip}",
        f"http://{ip}:80",
        f"https://{ip}:443"
    ]
    
    for url in urls:
        try:
            print(f"\nTesting web interface: {url}")
            response = requests.get(url, 
                                 auth=(username, password),
                                 verify=False,
                                 timeout=3)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                # Try to find RTSP URL in the response
                content = response.text.lower()
                print("\nSearching for RTSP configuration...")
                
                # Look for common RTSP-related text
                rtsp_indicators = [
                    'rtsp://', 
                    'streaming', 
                    'stream_url',
                    'camera_stream',
                    'video_url',
                    'media_url'
                ]
                
                for indicator in rtsp_indicators:
                    if indicator in content:
                        print(f"Found potential RTSP indicator: {indicator}")
                        # Print surrounding context
                        start = max(0, content.find(indicator) - 50)
                        end = min(len(content), content.find(indicator) + 50)
                        print(f"Context: ...{content[start:end]}...")
            
            return True
        except Exception as e:
            print(f"Error: {str(e)}")
    return False

def test_rtsp_paths(ip, username, password):
    # First test web interface
    if not test_web_interface(ip, username, password):
        print("WARNING: Could not access web interface")
    
    # Encode credentials
    encoded_username = urllib.parse.quote(username)
    encoded_password = urllib.parse.quote(password)
    
    # Update paths with discovered ONVIF profiles
    paths = [
        # Discovered ONVIF paths
        "ONVIF/MediaInput?profile=2_def_profile6",  # H264 1080p
        "ONVIF/MediaInput?profile=2_def_profile5",  # H264 360p
        "ONVIF/MediaInput?profile=2_def_profile4",  # H264 180p
        "ONVIF/MediaInput?profile=2_def_profile3",  # JPEG 1080p
        "ONVIF/MediaInput?profile=2_def_profile2",  # JPEG 360p
        "ONVIF/MediaInput?profile=2_def_profile1",  # JPEG 180p
        # Try variations
        "ONVIF/MediaInput",
        "ONVIF/MediaInput?profile=1",
        "ONVIF/MediaInput?profile=2",
    ]

    for path in paths:
        # Try URL with and without credentials
        urls = [
            f"rtsp://{encoded_username}:{encoded_password}@{ip}:554/{path}",
            f"rtsp://{ip}:554/{path}"
        ]

        for url in urls:
            print(f"\nTesting RTSP URL: {url}")
            
            # Try both TCP and UDP transport
            for transport in ['tcp', 'udp']:
                cmd = [
                    'ffprobe',
                    '-v', 'debug',  # Increased verbosity for debugging
                    '-rtsp_transport', transport,
                    '-i', url,
                    '-show_streams',
                    '-select_streams', 'v:0',
                    '-of', 'json',
                    '-timeout', '5000000'
                ]
                
                try:
                    print(f"Attempting connection using {transport.upper()}...")
                    result = subprocess.run(cmd, 
                                         capture_output=True, 
                                         text=True, 
                                         timeout=6)
                    
                    if result.returncode == 0:
                        print(f"Success! Found working stream using {transport.upper()}")
                        return url
                    else:
                        print(f"Failed ({transport.upper()}): {result.stderr.strip()}")
                except subprocess.TimeoutExpired:
                    print(f"Connection timed out ({transport.upper()})")
                except Exception as e:
                    print(f"Error: {str(e)}")
                
                time.sleep(1)
    
    return None

def save_camera_config(ip, username, password, working_url):
    """Save working camera configuration to a JSON file"""
    config = {
        'ip': ip,
        'username': username,
        'password': password,
        'rtsp_url': working_url,
        'last_tested': datetime.now().isoformat(),
        'profiles': {
            'high': working_url,
            'medium': working_url.replace('profile6', 'profile5'),
            'low': working_url.replace('profile6', 'profile4')
        }
    }
    
    config_dir = 'config'
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
        
    config_file = os.path.join(config_dir, f'camera_{ip.replace(".", "_")}.json')
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)
    
    print(f"\nCamera configuration saved to: {config_file}")

def test_stream_quality(url):
    """Test stream quality and performance"""
    print("\nTesting stream quality...")
    
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,codec_name,r_frame_rate,bit_rate',
        '-of', 'json',
        '-i', url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            info = json.loads(result.stdout)
            if 'streams' in info and len(info['streams']) > 0:
                stream = info['streams'][0]
                print("\nStream Information:")
                print(f"Resolution: {stream.get('width')}x{stream.get('height')}")
                print(f"Codec: {stream.get('codec_name')}")
                print(f"Frame Rate: {stream.get('r_frame_rate')}")
                print(f"Bit Rate: {stream.get('bit_rate', 'N/A')} bps")
                return True
    except Exception as e:
        print(f"Error testing stream: {str(e)}")
    return False

if __name__ == "__main__":
    ip = "192.168.100.18"
    username = "admin"
    password = "teltex@4679$"
    
    print("\n=== RTSP Camera Connection Test ===")
    print(f"Target: {ip}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    
    working_url = test_rtsp_paths(ip, username, password)
    
    if (working_url):
        print("\n=== Success! ===")
        print(f"Working RTSP URL: {working_url}")
        
        # Save configuration
        save_camera_config(ip, username, password, working_url)
        
        # Test stream quality
        test_stream_quality(working_url)
        
        print("\nTest with VLC:")
        print(f"/Applications/VLC.app/Contents/MacOS/VLC --rtsp-tcp '{working_url}'")
        
        print("\nTest with FFplay:")
        print(f"ffplay -rtsp_transport tcp '{working_url}'")
        
        print("\nPython OpenCV Example:")
        print(f"""
import cv2

url = '{working_url}'
print(f"Connecting to: {{url}}")

cap = cv2.VideoCapture(url)
if not cap.isOpened():
    print("Failed to open stream")
    exit(1)

cv2.namedWindow('Camera Stream', cv2.WINDOW_NORMAL)

while True:
    ret, frame = cap.read()
    if ret:
        cv2.imshow('Camera Stream', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    else:
        print("Failed to read frame")
        break

cap.release()
cv2.destroyAllWindows()
""")
    else:
        print("\n=== No Working URL Found ===")
        print("\nTroubleshooting Steps:")
        print("1. Try accessing web interface in browser:")
        print(f"   http://{ip}")
        print(f"   https://{ip}")
        print("2. Check camera documentation for correct RTSP path")
        print("3. Verify network connectivity (firewall rules)")
        print("4. Double-check username/password")
        print("5. Try ONVIF Device Manager to discover camera")