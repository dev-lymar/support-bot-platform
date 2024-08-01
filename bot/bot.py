import asyncio
import os
import logging
import httpx

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
WS_URL = os.getenv("WS_URL")

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initializing the bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
@dp.message(Command("help"))
async def send_welcome(message: Message):
    await message.answer("Hi! I am your support bot.")


@dp.message(lambda message: message.chat.type == "supergroup" and message.reply_to_message)
async def handle_group_message(message: types.Message):
    if message.chat.id == int(GROUP_CHAT_ID):
        reply_text = message.reply_to_message.text
        if reply_text:
            question_id = extract_question_id(reply_text)
            if question_id:
                user_id = await get_user_id_by_question_id(question_id)
                if user_id:
                    await bot.send_message(user_id, f"Manager replied:\n\n{message.text}")
                    async with httpx.AsyncClient() as client:
                        await client.post(f"{WS_URL}/ws/{user_id}", json={"message": message.text})


# Helper function to extract the question ID from the message
def extract_question_id(text):
    parts = text.split("Question ID: ")
    if len(parts) > 1:
        try:
            return int(parts[1].strip())
        except ValueError:
            logger.error("Failed to parse question ID from text.")
    return None


# Helper function to get user ID by question ID
async def get_user_id_by_question_id(question_id):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://localhost:8000/questions/{question_id}")
        if response.status_code == 200:
            return response.json().get("user_id")
    return None


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
