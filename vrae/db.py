import aiomysql
import logging
from . import app

async def execute_query(query, params=None):
    try:
        pool = await aiomysql.create_pool(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            db=app.config['MYSQL_DB'],
            autocommit=True
        )
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                if query.strip().upper().startswith('SELECT'):
                    result = await cur.fetchall()
                else:
                    result = cur.lastrowid
                await conn.commit()
                return result
                
    except Exception as e:
        app.logger.error(f"Database error: {str(e)}")
        raise
    finally:
        pool.close()
        await pool.wait_closed()