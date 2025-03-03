import asyncio
from vrae import app
from vrae.init_db import init_db

async def main():
    await init_db(app)

if __name__ == "__main__":
    asyncio.run(main())