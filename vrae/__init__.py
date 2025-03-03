from quart import Quart
from quart_cors import cors
from quart_auth import QuartAuth
import logging
import os
from logging.handlers import RotatingFileHandler
from .config import Config
from .init_db import init_db

# Initialize Quart app
app = Quart(__name__)

# Configure CORS with expanded settings
app = cors(app, 
    allow_origin=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Access-Control-Allow-Credentials"],
    allow_credentials=True,
    max_age=3600
)

# Load configuration
app.config.update(
    SECRET_KEY=Config.SECRET_KEY,
    MYSQL_HOST=Config.MYSQL_HOST,
    MYSQL_USER=Config.MYSQL_USER,
    MYSQL_PASSWORD=Config.MYSQL_PASSWORD,
    MYSQL_DB=Config.MYSQL_DB,
    QUART_AUTH_COOKIE_SECURE=False,
    QUART_AUTH_COOKIE_HTTPONLY=True
)

# Setup auth
auth = QuartAuth(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

os.makedirs('logs', exist_ok=True)
log_handler = RotatingFileHandler(
    'logs/api.log', 
    mode='a', 
    maxBytes=5 * 1024 * 1024, 
    backupCount=2
)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.DEBUG)

app.logger.addHandler(log_handler)
root_logger = logging.getLogger()
root_logger.addHandler(log_handler)
root_logger.setLevel(logging.DEBUG)

# Initialize database
@app.before_serving
async def startup():
    await init_db(app)

# Import routes after app initialization
from . import routes
