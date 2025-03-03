from quart import request, jsonify, Response, websocket
from quart_auth import login_required, current_user
from . import app
from functools import wraps
import jwt
import logging
from .models import User, LoginLog, Device
from .stream import StreamManager  # Import StreamManager first
from .webrtc_stream import VideoStreamTrack
from aiortc import RTCPeerConnection, RTCSessionDescription
from .camera_manager import CameraManager

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
def login():
    app.logger.info("Entering /login route")  # Alterado aqui
    auth = request.get_json()
    app.logger.debug(f"Received login request: {auth}")  # Alterado aqui

    if (not auth or not auth['username'] or not auth['password']):
        app.logger.warning("Authentication data is missing!")  # Alterado aqui
        return jsonify({'message': 'Erro de autenticação!'}), 401

    user = User.get_by_username(auth['username'])
    if (user):
        app.logger.debug(f"User found: {user.username}")  # Alterado aqui
    else:
        app.logger.warning(f"User not found with username: {auth['username']}")  # Alterado aqui

    if (not user or not user.check_password(auth['password'])):
        app.logger.warning("Authentication failed!")  # Alterado aqui
        return jsonify({'message': 'Erro de autenticação!'}), 401

    # Gerar o token
    token = jwt.encode({
        'id': user.id
    }, app.config['SECRET_KEY'], algorithm='HS256')
    app.logger.debug(f"Token generated for user {user.username}: {token}")  # Alterado aqui

    # Inserir o login na tabela login_logs
    try:
        LoginLog.add_log(user.id, token)

    except mysql.connector.Error as err:
        app.logger.error(f"Error saving login data: {err}")  # Alterado aqui
        return jsonify({'message': 'Erro ao registrar o login!'}), 500

    # Login com sucesso
    response = jsonify({'token': token})
    return log_request(response)


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
def register():
    app.logger.info("Entering /register route")  # Alterado aqui
    auth = request.get_json()
    app.logger.debug(f"Received register request: {auth}")  # Alterado aqui

    if (not auth or not auth['username'] or not auth['password']):
        app.logger.warning("Register data is missing!")  # Alterado aqui
        return log_request(jsonify({'message': 'Erro de dados!'})), 401

    # Test Database Connection
    try:
        mydb = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        mydb.close()
        app.logger.debug("Database connection test successful")  # Alterado aqui
    except mysql.connector.Error as err:
        app.logger.error(f"Database connection error: {err}")  # Alterado aqui
        return log_request(jsonify({'message': 'Database connection error'})), 500

    result = User.add_user(auth['username'], auth['password'])
    if (result):
        app.logger.debug(f"User registered with username: {auth['username']}")  # Alterado aqui
    else:
        app.logger.warning(f"Error registering user with username: {auth['username']}")  # Alterado aqui

    if (not result):
        return log_request(jsonify({'message': 'Erro ao adicionar!'})), 401

    response = jsonify({'message': 'Usuário adicionado com sucesso!'})
    return log_request(response)


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
    """WebRTC offer route"""
    try:
        params = await request.get_json()
        offer = RTCSessionDescription(
            sdp=params["sdp"],
            type=params["type"]
        )
        
        # Get device_id from request
        device_id = params.get("device_id")
        
        if device_id:
            # Verify if device exists and user has access
            device = await Device.get(device_id)
            if not device:
                return jsonify({'error': 'Device not found'}), 404

        pc = RTCPeerConnection()
        pcs.add(pc)
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            app.logger.info(f"Connection state is {pc.connectionState}")
            if pc.connectionState == "failed":
                await pc.close()
                pcs.discard(pc)

        # Add video track with specific device
        video = VideoStreamTrack(device_id)
        pc.addTrack(video)

        # Handle the offer
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        app.logger.info(f"WebRTC connection established for device {device_id}")
        return jsonify({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })

    except Exception as e:
        app.logger.error(f"Error in WebRTC connection: {str(e)}")
        return jsonify({'error': str(e)}), 500


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
