import asyncio
import aiohttp

async def main():
    async with aiohttp.ClientSession() as s:
        # We need an admin user, maybe we don't know the credentials.
        # But wait, let's just make the request. 
        # Actually I can just check the uvicorn logs if it crashed!
        pass

if __name__ == "__main__":
    asyncio.run(main())
