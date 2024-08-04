import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from dotenv import load_dotenv
import websockets
import redis.asyncio as redis

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
WS_URL = os.getenv("WS_URL")
REDIS_URL = os.getenv("REDIS_URL")

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initializing the bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Connecting to Redis
redis_client = redis.from_url(REDIS_URL)


@dp.message(lambda message: message.chat.type == "supergroup")
async def handle_group_message(message: types.Message):
    if message.chat.id == int(GROUP_CHAT_ID):
        logger.info(f"Handling message in group: {message.chat.id}, topic_id: {message.message_thread_id}")

        if message.is_topic_message:
            topic_id = message.message_thread_id

            # Retrieve question_id and user_id from Redis
            question_id = await redis_client.get(f"topic:{topic_id}:question_id")
            user_id = await redis_client.get(f"topic:{topic_id}:user_id")

            if question_id and user_id:
                question_id = question_id.decode('utf-8')
                user_id = user_id.decode('utf-8')
                logger.info(f"Found question_id: {question_id} and user_id: {user_id} for topic_id: {topic_id}")

                ws_url = f"{WS_URL}/ws/{user_id}"
                logger.info(f"Connecting to WebSocket URL: {ws_url}")

                try:
                    async with websockets.connect(ws_url) as websocket:
                        await websocket.send(message.text)
                        logger.info(f"Message sent to user {user_id} via WebSocket")
                except Exception as e:
                    logger.error(f"Failed to send message to user {user_id} via WebSocket: {e}")
            else:
                logger.warning(f"No mapping found for topic_id {topic_id}")
        else:
            logger.info("Message is not a topic message.")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
