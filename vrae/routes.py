from quart import request, jsonify, Response, websocket
from quart_auth import login_required, current_user
from . import app
from functools import wraps
import jwt
import logging
from .models import User, LoginLog, Device
from .stream import StreamManager  # Import StreamManager first
from .webrtc_stream import VideoStreamTrack
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from .camera_manager import CameraManager

# Define RTCConfiguration no início do arquivo, após os imports
rtc_configuration = RTCConfiguration([
    RTCIceServer(urls=["stun:stun.l.google.com:19302"])
])

# Create StreamManager instance after import
stream_manager = StreamManager()

def token_required(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        try:
            logging.debug("Entering token_required decorator")
            token = request.headers.get('Authorization')
            
            if not token:
                logging.error("No token provided")
                return jsonify({'message': 'Token is missing!'}), 401

            # Remove 'Bearer ' if present
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
            
            logging.debug(f"Decoding token: {token}")
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            
            # Add user data to kwargs instead of positional args
            kwargs['user_data'] = data
            return await f(*args, **kwargs)
            
        except jwt.InvalidTokenError as e:
            logging.error(f"Token validation error: {str(e)}")
            return jsonify({'message': 'Token inválido'}), 401
        except Exception as e:
            logging.error(f"Unexpected error in token validation: {str(e)}", exc_info=True)
            return jsonify({'message': 'Erro na validação do token'}), 500
    
    return decorated


@app.route('/login', methods=['POST'])
async def login():
    app.logger.info("Entering /login route")
    try:
        auth = await request.get_json()
        app.logger.debug(f"Received login request: {auth}")

        if not auth or not auth.get('username') or not auth.get('password'):
            return jsonify({'message': 'Dados inválidos!'}), 401

        user = await User.get_by_username(auth['username'])
        if not user:
            return jsonify({'message': 'Usuário não encontrado!'}), 401

        if not user.check_password(auth['password']):
            return jsonify({'message': 'Senha incorreta!'}), 401

        # Gerar o token
        token = jwt.encode({
            'id': user.id,  # Agora user.id existe
            'username': user.username
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        app.logger.debug(f"Token generated for user {user.username}: {token}")

        # Registrar o login
        await LoginLog.add_log(user.id, token)  # Tornar add_log async também

        return jsonify({
            'token': token,
            'message': 'Login realizado com sucesso!'
        }), 200

    except Exception as e:
        app.logger.error(f"Error in login route: {str(e)}")
        return jsonify({'message': 'Erro interno!'}), 500


@app.route('/protected', methods=['POST'])
@token_required
def protected_route(current_user):
    if (not current_user):
        return jsonify({'message': 'Erro interno ao recuperar usuário'}), 500

    return jsonify({
        'message': 'This is a protected route',
        'user': current_user.username
    })


@app.route('/register', methods=['POST'])
async def register():
    app.logger.info("Entering /register route")
    try:
        auth = await request.get_json()
        app.logger.debug(f"Received register request: {auth}")

        if not auth or not auth.get('username') or not auth.get('password'):
            app.logger.warning("Register data is missing!")
            return jsonify({'message': 'Erro de dados!'}), 401

        # Verificar se usuário já existe
        existing_user = await User.get_by_username(auth['username'])
        if existing_user:
            app.logger.warning(f"User {auth['username']} already exists")
            return jsonify({'message': 'Usuário já existe!'}), 409

        result = await User.add_user(auth['username'], auth['password'])
        if result:
            return jsonify({'message': 'Usuário registrado com sucesso!'}), 201
        else:
            return jsonify({'message': 'Erro ao adicionar!'}), 401

    except Exception as e:
        app.logger.error(f"Error in register route: {str(e)}")
        return jsonify({'message': 'Erro interno!'}), 500


@app.route('/streaming')
@login_required
async def streaming_route():
    """Video streaming route."""
    return Response(
        await stream_manager.generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS'
        }
    )


@app.route('/stop_streaming', methods=['POST'])
@token_required
def stop_streaming_route(current_user):
    return get_stop_stream_response(current_user)


pcs = set()

@app.route('/offer', methods=['POST'])
@token_required
async def offer(user_data):
    pc = None
    video = None
    try:
        data = await request.get_json()
        device_id = data.get('device_id')
        if not device_id:
            return jsonify({"error": "No device_id provided"}), 400

        logging.info(f"Creating WebRTC connection for device {device_id}")
        
        video = VideoStreamTrack(device_id=device_id)
        await video.connect_to_camera()

        pc = RTCPeerConnection(configuration=rtc_configuration)
        pc.addTrack(video)
        app.pc_pool.add(pc)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logging.info(f"Connection state: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed"]:
                if video:
                    video.stop()
                if pc in app.pc_pool:
                    app.pc_pool.discard(pc)

        offer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
        await pc.setRemoteDescription(offer)
        
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return jsonify({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })

    except Exception as e:
        logging.error(f"Error in offer route: {str(e)}", exc_info=True)
        if video:
            video.stop()
        if pc:
            await pc.close()
        return jsonify({"error": str(e)}), 500

@app.route('/devices', methods=['GET'])
@token_required
async def list_devices(user_data):  # Added user_data parameter
    try:
        devices = await Device.get_devices(user_id=user_data['id'])  # Pass user_id to get_devices
        return jsonify(devices)
    except Exception as e:
        logging.error(f"Error listing devices: {str(e)}")
        return jsonify({'message': 'Error listing devices'}), 500

@app.route('/devices', methods=['POST'])
@token_required
async def add_device(user_data):  # Now accepts user_data from token_required
    try:
        data = await request.get_json()
        logging.debug(f"Received device data: {data}")
        
        # Initialize camera manager and test connection
        camera_manager = CameraManager()
        connection_success = await camera_manager.connect_camera(data)
        
        if not connection_success:
            return jsonify({'message': 'Failed to connect to camera'}), 400
        
        # Add user_id from token to device data
        data['user_id'] = user_data.get('id')
        
        # Add device to database
        logging.info("Adding device to database")
        result = await Device.add_device(data)
        
        return jsonify({
            'message': 'Device added successfully',
            'device_id': result.get('device_id')
        }), 201
            
    except Exception as e:
        logging.error(f"Error in add_device: {str(e)}", exc_info=True)
        return jsonify({'message': str(e)}), 500


@app.after_request
async def after_request(response):
    try:
        content_type = response.headers.get('Content-Type', '')
        
        log_data = {
            'date_created': str(getattr(response, 'date', None)),
            'module': request.path,
            'payload': 'No JSON Payload',
            'response': ''
        }

        # Skip binary responses
        if 'image' in content_type or 'video' in content_type:
            log_data['response'] = f'Binary data ({content_type})'
        else:
            try:
                response_data = await response.get_data()
                if response_data:
                    if 'application/json' in content_type:
                        log_data['response'] = response_data.decode('utf-8')
                    elif 'text' in content_type:
                        log_data['response'] = response_data.decode('utf-8')
            except Exception as e:
                log_data['response'] = f'Error getting response data: {str(e)}'

        if request.is_json:
            try:
                json_data = await request.get_json()
                log_data['payload'] = json_data
            except Exception as e:
                log_data['payload'] = f'Error parsing JSON: {str(e)}'
            
        app.logger.info(log_data)
        
    except Exception as e:
        app.logger.error(f"Error in after_request: {str(e)}")
    
    return response

# Add this before app.run() or in your main block
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
