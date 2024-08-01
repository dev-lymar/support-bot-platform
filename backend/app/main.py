import os
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from pydantic import BaseModel
import httpx
import uvicorn
from dotenv import load_dotenv
import redis.asyncio as redis

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI()

# Connecting to Redis
redis_client = redis.from_url(os.getenv("REDIS_URL"))

# Loading tokens and URLs from environment variables
BOT_API_TOKEN = os.getenv("API_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
BOT_API_URL = f"https://api.telegram.org/bot{BOT_API_TOKEN}"


# WebSocket manager to manage connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocet: WebSocket):
        await websocet.accept()
        self.active_connections[user_id] = websocet

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await redis_client.rpush(f"user:{user_id}:messages", data)
    except WebSocketDisconnect:
        manager.disconnect(user_id)


# Model to request
class QuestionRequest(BaseModel):
    user_id: str
    user_name: str
    question_text: str


@app.post("/ask")
async def create_question(request: QuestionRequest):
    user_name = request.user_name
    user_id = request.user_id
    question_text = request.question_text
    topic_text = f"New question from {user_name}:\n\n{question_text}\n\nQuestion ID: {user_id}"

    async with httpx.AsyncClient() as client:
        logger.info(f"Preparing to send message to Telegram: chat_id={GROUP_CHAT_ID}, text={topic_text}")
        try:
            responce = await client.post(f"{BOT_API_URL}/sendMessage", json={
                "chat_id": GROUP_CHAT_ID,
                "text": topic_text
            })

            responce.raise_for_status()
            logger.info(f"Message sent successfully. Response: {responce.json()}")
            message_id = responce.json().get("result", {}).get("message_id")
            if message_id:
                logger.info(f"Creating forum topic with message_id={message_id}")
                forum_topic_response = await client.post(f"{BOT_API_URL}/createForumTopic", json={
                    "chat_id": GROUP_CHAT_ID,
                    "name": f"Dialogue with {user_name}",
                    "icon_color": 0x6FB9F0
                })

                forum_topic_response.raise_for_status()
                logger.info(f"Forum topic created successfully. Response: {forum_topic_response.json()}")

                topic_id = forum_topic_response.json()["result"]["message_thread_id"]
                await client.post(f"{BOT_API_URL}/sendMessage", json={
                    "chat_id": GROUP_CHAT_ID,
                    "message_thread_id": topic_id,
                    "text": topic_text
                })

                # Saving the message in Redis
                await redis_client.rpush(f"user:{user_id}:messages", topic_text)
                await manager.send_personal_message(topic_text, user_id)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

    return {"status": "success", "message": "Question sent to Telegram"}


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
