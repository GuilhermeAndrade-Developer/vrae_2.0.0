import asyncio
import aiomysql
import logging
from .config import Config

async def init_db(app):
    try:
        # Read schema file
        with open('schema.sql', 'r') as f:
            schema = f.read()

        # Connect to database
        pool = await aiomysql.create_pool(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            db=Config.MYSQL_DB,
            autocommit=True
        )

        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Split and execute multiple statements
                statements = schema.split(';')
                for statement in statements:
                    if statement.strip():
                        await cur.execute(statement)
                await conn.commit()
                
        app.logger.info("Database initialized successfully")
        
    except Exception as e:
        app.logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        pool.close()
        await pool.wait_closed()