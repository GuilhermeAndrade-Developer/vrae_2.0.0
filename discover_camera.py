from onvif import ONVIFCamera
import zeep
import logging

logging.basicConfig(level=logging.DEBUG)

def zeep_pythonvalue(xml_value):
    return xml_value

def discover_camera(ip, username, password):
    print(f"\n=== Testing ONVIF Connection to {ip} ===")
    try:
        # Initialize ONVIF camera
        cam = ONVIFCamera(ip, 80, username, password)
        zeep.xsd.simple.AnySimpleType.pythonvalue = zeep_pythonvalue
        
        # Create media service
        media = cam.create_media_service()
        
        # Get camera profiles
        profiles = media.GetProfiles()
        
        print(f"\nFound {len(profiles)} media profiles:")
        for profile in profiles:
            print(f"\nProfile: {profile.Name}")
            
            # Get stream URI
            stream_setup = {
                'Stream': 'RTP-Unicast',
                'Transport': {
                    'Protocol': 'RTSP'
                }
            }
            
            uri = media.GetStreamUri({
                'ProfileToken': profile.token,
                'StreamSetup': stream_setup
            })
            
            print(f"RTSP URL: {uri.Uri}")
            
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    ip = "192.168.100.18"
    username = "admin"
    password = "teltex@4679$"
    
    discover_camera(ip, username, password)