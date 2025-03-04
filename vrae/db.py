import aiomysql
import logging
from .config import Config

class Database:
    _pool = None

    @classmethod
    async def get_pool(cls):
        if cls._pool is None:
            try:
                cls._pool = await aiomysql.create_pool(
                    host=Config.MYSQL_HOST,
                    user=Config.MYSQL_USER,
                    password=Config.MYSQL_PASSWORD,
                    db=Config.MYSQL_DB,
                    autocommit=True,
                    charset='utf8mb4'
                )
                logging.info("Database pool created successfully")
            except Exception as e:
                logging.error(f"Error creating database pool: {str(e)}")
                raise
        return cls._pool

    @classmethod
    async def execute_query(cls, query, params=None):
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params or ())
                if query.strip().upper().startswith('SELECT'):
                    result = await cur.fetchall()
                else:
                    result = cur.lastrowid
                    await conn.commit()
                return result

    @classmethod
    async def close_pool(cls):
        if cls._pool is not None:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
            logging.info("Database pool closed")

    @classmethod
    async def init_db(cls):
        try:
            # Read schema file
            with open('schema.sql', 'r') as f:
                schema = f.read()

            pool = await cls.get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Split and execute multiple statements
                    statements = schema.split(';')
                    for statement in statements:
                        if statement.strip():
                            await cur.execute(statement)
                    await conn.commit()
            
            logging.info("Database initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing database: {str(e)}")
            raise

# Create an alias for the execute_query method to maintain compatibility
execute_query = Database.execute_query