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
        app.logger.debug("Entering token_required decorator")
        token = None

        # Check Authorization header
        auth_header = request.headers.get('Authorization')
        if (auth_header):
            if ('Bearer ' in auth_header):
                token = auth_header.split(" ")[1]
            else:
                token = auth_header

        # Check URL parameters if no header token
        if (not token and request.args.get('token')):
            token = request.args.get('token')

        if (not token):
            app.logger.warning("Token is missing")
            return jsonify({'message': 'Token não fornecido'}), 401

        try:
            app.logger.debug(f"Decoding token: {token}")
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = await User.get(data['id'])
            
            if (not current_user):
                app.logger.warning(f"User not found for ID: {data['id']}")
                return jsonify({'message': 'Usuário não encontrado'}), 401
                
            return await f(current_user, *args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            app.logger.warning("Token expired")
            return jsonify({'message': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            app.logger.warning("Invalid token")
            return jsonify({'message': 'Token inválido'}), 401
        except Exception as e:
            app.logger.error(f"Token validation error: {str(e)}")
            return jsonify({'message': 'Erro na validação do token'}), 401

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
async def offer(current_user):
    try:
        params = await request.get_json()
        offer = RTCSessionDescription(
            sdp=params["sdp"],
            type=params["type"]
        )

        # Use rtc_configuration ao invés de RTCConfiguration
        pc = RTCPeerConnection(configuration=rtc_configuration)
        pcs.add(pc)

        try:
            # Tente primeiro a câmera 1 (que funcionou no teste)
            video = VideoStreamTrack(camera_id=1)
        except Exception as e:
            app.logger.warning(f"Failed to open camera 1: {str(e)}")
            try:
                # Fallback para câmera 0
                video = VideoStreamTrack(camera_id=0)
            except Exception as e:
                app.logger.error(f"Failed to open any camera: {str(e)}")
                return jsonify({"error": "Could not initialize camera"}), 500

        pc.addTrack(video)

        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return jsonify({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })

    except Exception as e:
        app.logger.error(f"Error in WebRTC connection: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/devices', methods=['GET'])
@token_required
async def list_devices(current_user):
    """List all devices"""
    try:
        devices = await Device.get_devices()
        return jsonify([{
            'id': d.id,
            'name': d.name,
            'protocol': d.protocol,
            'ip': d.ip,
            'model': d.model,
            'username': d.username,
            'created_at': str(d.created_at)
        } for d in devices])
    except Exception as e:
        app.logger.error(f"Error listing devices: {e}")
        return jsonify({'message': 'Erro ao listar dispositivos'}), 500

@app.route('/devices', methods=['POST'])
@token_required
async def add_device(current_user):
    """Add a new device"""
    try:
        data = await request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'protocol', 'ip']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'Campo {field} é obrigatório'}), 400

        # Validate protocol
        valid_protocols = ['RTSP', 'HTTP', 'ONVIF']
        if data['protocol'] not in valid_protocols:
            return jsonify({'message': 'Protocolo inválido'}), 400

        # Test camera connection and get model
        success, model = await CameraManager.test_connection(
            protocol=data['protocol'],
            ip=data['ip'],
            username=data.get('username'),
            password=data.get('password')
        )

        if not success:
            return jsonify({'message': 'Não foi possível conectar ao dispositivo'}), 400

        # Add device with model information
        result = await Device.add_device(
            name=data['name'],
            protocol=data['protocol'],
            ip=data['ip'],
            username=data.get('username'),
            password=data.get('password'),
            model=model
        )

        if result:
            return jsonify({
                'message': 'Dispositivo adicionado com sucesso',
                'model': model
            }), 201
        return jsonify({'message': 'Erro ao adicionar dispositivo'}), 500

    except Exception as e:
        app.logger.error(f"Error adding device: {e}")
        return jsonify({'message': f'Erro ao adicionar dispositivo: {str(e)}'}), 500


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
