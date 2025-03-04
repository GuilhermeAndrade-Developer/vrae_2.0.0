import asyncio
import logging
from vrae.db import Database

async def main():
    logging.basicConfig(level=logging.INFO)
    try:
        await Database.init_db()
    finally:
        await Database.close_pool()

if __name__ == "__main__":
    asyncio.run(main())