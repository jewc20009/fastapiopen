from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from flowise import Flowise, PredictionData
import json
import os
from dotenv import load_dotenv
import time
import asyncio

load_dotenv()

app = FastAPI()

client = Flowise(base_url=os.getenv("BASE_URL"), api_key=os.getenv("JWT"))

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    question = data.get('question', '')
    chatflow_id = data.get('chatflow_id', '680b56dd-7183-418a-b36a-7219d4646bf1')

    async def generate():
        completion = client.create_prediction(
            PredictionData(
                chatflowId=chatflow_id,
                question=question,
                streaming=True,
                overrideConfig={"SessionId": chatflow_id}
            )
        )

        for chunk in completion:
            try:
                chunk_data = json.loads(chunk)
                if "data" in chunk_data:
                    for data in chunk_data["data"]:
                        if isinstance(data, dict) and "messages" in data:
                            message = data["messages"][0] if data["messages"] else ""
                            response = {
                                "id": f"chatcmpl-{time.time()}",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": f"flowise-{chatflow_id}",
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {
                                            "content": message
                                        },
                                        "finish_reason": None
                                    }
                                ]
                            }
                            yield json.dumps(response) + "\n"
                            await asyncio.sleep(0)  # Allow other tasks to run
            except json.JSONDecodeError:
                yield json.dumps({"error": f"Error decoding JSON from chunk: {chunk}"}) + "\n"
                await asyncio.sleep(0)

        # Send the final message to indicate completion
        final_response = {
            "id": f"chatcmpl-{time.time()}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": f"flowise-{chatflow_id}",
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield json.dumps(final_response) + "\n"

    return StreamingResponse(generate(), media_type="application/json")

