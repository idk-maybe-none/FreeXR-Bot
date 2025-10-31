import asyncio
from bot import bot
from config import TOKEN

async def main():
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())