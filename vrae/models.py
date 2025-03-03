from quart_auth import AuthUser
from werkzeug.security import generate_password_hash, check_password_hash
from .db import execute_query
import logging
from datetime import datetime


class User(AuthUser):
    def __init__(self, auth_id: str, username: str, password_hash: str = None, id: int = None):
        super().__init__(auth_id)
        self.username = username
        self.password_hash = password_hash
        self.id = id  # Adicionando o id

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password) if self.password_hash else False

    @staticmethod
    async def get(user_id: int):
        try:
            query = "SELECT id, username, password_hash FROM users WHERE id = %s"
            result = await execute_query(query, (user_id,))
            if result and result[0]:
                return User(str(result[0][0]), result[0][1], result[0][2])
            return None
        except Exception as e:
            logging.error(f"Error fetching user: {e}")
            return None

    @staticmethod
    async def get_by_username(username):
        try:
            query = "SELECT id, username, password_hash FROM users WHERE username = %s"
            result = await execute_query(query, (username,))
            
            if result and len(result) > 0:
                user_data = result[0]
                return User(
                    auth_id=str(user_data[0]),  # Convertendo id para string para auth_id
                    username=user_data[1],
                    password_hash=user_data[2],
                    id=user_data[0]  # Adicionando o id aqui
                )
            return None
        except Exception as e:
            logging.error(f"Error getting user by username: {e}")
            return None

    @staticmethod
    async def add_user(username, password):  # Adicionar async aqui
        try:
            query = "INSERT INTO users (username, password_hash) VALUES (%s, %s)"
            params = (username, generate_password_hash(password))
            result = await execute_query(query, params)  # Usar execute_query async
            return bool(result)
        except Exception as e:
            logging.error(f"Error adding user: {e}")
            return False

    @staticmethod
    def get_by_id(user_id):
        try:
            mydb = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB
            )
            mycursor = mydb.cursor()

            logging.debug(f"Fetching user by ID: {user_id}")
            mycursor.execute("SELECT id, username, password_hash FROM users WHERE id = %s", (user_id,))
            result = mycursor.fetchone()

            if result:
                logging.debug(f"User found: {result[1]}")
                return User(result[0], result[1], result[2])
            else:
                logging.warning(f"No user found with ID: {user_id}")
                return None
        except mysql.connector.Error as err:
            logging.error(f"Database error: {err}")
            return None
        finally:
            if mycursor:
                mycursor.close()
            if mydb:
                mydb.close()


class LoginLog:
    @staticmethod
    async def add_log(user_id, token):  # Tornar método async
        try:
            query = "INSERT INTO login_logs (user_id, token) VALUES (%s, %s)"
            await execute_query(query, (user_id, token))  # Usar execute_query async
            return True
        except Exception as e:
            logging.error(f"Error adding login log: {e}")
            return False


class Device:
    def __init__(self, id, name, protocol, ip, model=None, username=None, password=None, created_at=None):
        self.id = id
        self.name = name
        self.protocol = protocol
        self.ip = ip
        self.model = model
        self.username = username
        self.password = password
        self.created_at = created_at

    @staticmethod
    async def add_device(name, protocol, ip, model=None, username=None, password=None):
        try:
            query = """
                INSERT INTO devices (name, protocol, ip, model, username, password)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (name, protocol, ip, model, username, password)
            result = await execute_query(query, params)
            return bool(result)
        except Exception as e:
            app.logger.error(f"Error adding device: {e}")
            return False

    @staticmethod
    async def get_devices():
        try:
            query = "SELECT id, name, protocol, ip, model, username, password, created_at FROM devices"
            result = await execute_query(query)
            
            devices = []
            for row in result:
                device = Device(
                    id=row[0],
                    name=row[1],
                    protocol=row[2],
                    ip=row[3],
                    model=row[4],
                    username=row[5],
                    password=row[6],
                    created_at=row[7]
                )
                devices.append(device)
            return devices
        except Exception as e:
            app.logger.error(f"Error getting devices: {e}")
            return []
