[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=Python&logoColor=yellow)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.10.0-3776AB?style=flat&logo=telegram&logoColor=white")](https://aiogram.dev/)
[![Redis](https://img.shields.io/badge/Redis-5.0.8-DC382D?style=flat&logo=Redis&logoColor=white)](https://redis.io/)

# support-bot-platform

### Table of contents:
- [Project Description](#Project-Description)
- [Getting Started](#Getting-Started)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Project Description

This project is a messaging system that integrates Telegram group chat management with WebSocket communication. 
It allows users to ask questions via a FastAPI web service, which then creates a corresponding topic in a Telegram group chat. 
Responses in the group chat are relayed back to the user via WebSocket, allowing for real-time interaction.

***Key components:***

- **Telegram Bot**: Handles incoming messages in a Telegram group chat, relaying relevant messages to users via WebSocket.
- **FastAPI Service**: Provides endpoints for users to submit questions and retrieve messages.
- **WebSocket Communication**: Manages real-time communication between users and the system.
- **Redis**: Used for storing question and user information, as well as caching messages.

## Getting Started

Ensure you have the following installed:

- Python 3.12+ 
- Redis
- A Telegram bot token

1. Clone the repository and navigate to the project directory:

```sh
git clone https://github.com/dev-lymar/support-bot-platform.git
cd support-bot-platform
```
2. Configure .env
```sh
replace env.example with your data
```
3. Install dependencies:
```sh
pip install -r requirements.txt
```
### Running the Application
***Start Redis:***
Ensure Redis is running on your machine.
You can start it with the following command if you have Redis installed:
```sh
redis-server
```
**Start the Telegram bot and WebSocket server**

Navigate to the directory containing the bot script and run:
```sh
python bot.py
```
**Start the FastAPI server:**

Navigate to the directory containing the FastAPI application and run:
```sh
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Usage
### Submitting a Question
To submit a question, send a POST request to the /ask endpoint with the following JSON payload:

```sh
{
    "user_name": "YourName",
    "question_text": "Your question goes here."
}
```
Example using curl:
```sh
curl -X POST "http://localhost:8000/ask" -H "Content-Type: application/json" -d '{"user_name": "Alice", "question_text": "What is the capital of France?"}'
```

### Retrieving Messages

***Get Question Messages***

To retrieve messages related to a specific question, send a GET request to the ```/questions/{question_id}``` endpoint.
Example using curl:
```sh
curl -X GET "http://localhost:8000/questions/<question_id>"
```

***Get User Messages***

To retrieve all messages for a specific user, send a GET request to the ```/user/{user_id}/```messages endpoint.

Example using curl:
```sh
curl -X GET "http://localhost:8000/user/<user_id>/messages"
```

***WebSocket Communication***
Connect to the WebSocket server at ```ws://localhost:8000/ws/{user_id}``` to receive real-time messages related to your question.


*By following these instructions, you can set up and use the application to manage Telegram group chats and interact with users in real-time.*

## Contributing
If you would like to contribute to this project, please fork the repository and submit a pull request. 
For major changes, please open an issue first to discuss what you would like to change.

## License
This project is licensed under the MIT License. See the LICENSE file for details.