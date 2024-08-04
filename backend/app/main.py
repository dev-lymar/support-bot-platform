import os
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, constr, field_validator
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

# Default time-to-live for Redis keys (in seconds)
DEFAULT_TTL = 3600  # 1 hour


# WebSocket manager to manage connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)
        else:
            logger.info(f"User {user_id} is not connected to WebSocket. Saving message to Redis.")
            await redis_client.rpush(f"user:{user_id}:messages", message)
            await redis_client.expire(f"user:{user_id}:messages", DEFAULT_TTL)


manager = ConnectionManager()


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await redis_client.rpush(f"user:{user_id}:messages", data)
            await redis_client.expire(f"user:{user_id}:messages", DEFAULT_TTL)
    except WebSocketDisconnect:
        manager.disconnect(user_id)


class QuestionRequest(BaseModel):
    user_name: constr(min_length=1, max_length=50)
    question_text: constr(min_length=1, max_length=500)

    @field_validator('user_name')
    def validate_user_name(cls, v):
        if not v.isalnum():
            raise ValueError('User name must be alphanumeric.')
        return v


@app.post("/ask")
async def create_question(request: QuestionRequest):
    user_name = request.user_name
    question_text = request.question_text
    user_id = str(os.urandom(8).hex())
    question_id = user_id

    topic_text = f"New question from {user_name}:\n\n{question_text}\n\nQuestion ID: {question_id}"

    async with httpx.AsyncClient() as client:
        try:
            forum_topic_response = await client.post(f"{BOT_API_URL}/createForumTopic", json={
                "chat_id": GROUP_CHAT_ID,
                "name": f"Dialogue with {user_name}",
                "icon_color": 0x6FB9F0
            })
            forum_topic_response.raise_for_status()

            topic_id = forum_topic_response.json()["result"]["message_thread_id"]
            response = await client.post(f"{BOT_API_URL}/sendMessage", json={
                "chat_id": GROUP_CHAT_ID,
                "message_thread_id": topic_id,
                "text": topic_text
            })
            response.raise_for_status()

            await redis_client.set(f"topic:{topic_id}:question_id", question_id, ex=DEFAULT_TTL)
            await redis_client.set(f"topic:{topic_id}:user_id", user_id, ex=DEFAULT_TTL)

            await redis_client.rpush(f"user:{user_id}:messages", topic_text)
            await redis_client.expire(f"user:{user_id}:messages", DEFAULT_TTL)
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

    return {"status": "success", "message": "Question sent to Telegram", "user_id": user_id}


@app.get("/questions/{question_id}")
async def get_question(question_id: str):
    messages = await redis_client.lrange(f"user:{question_id}:messages", 0, -1)
    if messages:
        return {"user_id": question_id, "messages": messages}
    raise HTTPException(status_code=404, detail="Question not found")


@app.get("/user/{user_id}/messages")
async def get_user_messages(user_id: str):
    messages = await redis_client.lrange(f"user:{user_id}:messages", 0, -1)
    if messages:
        return {"user_id": user_id, "messages": messages}
    raise HTTPException(status_code=404, detail="Messages not found")

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
