from quart import Quart
from quart_cors import cors
from quart_auth import QuartAuth
import logging
import os
import weakref
from aiortc import RTCPeerConnection
from logging.handlers import RotatingFileHandler
from .config import Config
from .db import Database

# Initialize Quart app
app = Quart(__name__)

# Initialize WebRTC peer connection pool
app.pc_pool = weakref.WeakSet()

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
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'logs/api.log',
            maxBytes=10000000,
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)

# Initialize database
@app.before_serving
async def init_db():
    try:
        await Database.get_pool()
        logging.info("Database connection initialized")
    except Exception as e:
        logging.error(f"Failed to initialize database: {str(e)}")
        raise

@app.after_serving
async def cleanup():
    await Database.close_pool()
    logging.info("Database connection closed")

# Import routes after app initialization
from . import routes
