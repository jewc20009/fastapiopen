from fastapi import FastAPI, Request, Header
from fastapi.responses import StreamingResponse
from flowise import Flowise, PredictionData
import json
import os
from dotenv import load_dotenv
import time
import asyncio

load_dotenv()

app = FastAPI()

client = Flowise(base_url="https://flowise-liy3.onrender.com", api_key=os.getenv("JWT"))

@app.post("/v1/chat/completions")
async def chat(request: Request, authorization: str = Header(None)):
    if not authorization.startswith("Bearer "):
        return {"error": "Invalid Authorization header"}
    
    session_id = authorization.split("Bearer ")[1]
    
    data = await request.json()
    chatflow_id = data.get('model', '')
    messages = data.get('messages', [])
    stream = data.get('stream', False)

    max_tokens = data.get('max_tokens')
    temperature = data.get('temperature')
    top_p = data.get('top_p')

    if not stream:
        return {"error": "Only streaming responses are supported"}

    system_message = next((msg['content'] for msg in messages if msg['role'] == 'system'), "")
    user_messages = [msg['content'] for msg in messages if msg['role'] == 'user']
    
    combined_prompt = f"{system_message}\n\n" + "\n".join(user_messages)

    override_config = {
        "sessionId": session_id,
        "chatHistory": messages,
    }

    if max_tokens is not None:
        override_config["maxTokens"] = max_tokens
    if temperature is not None:
        override_config["temperature"] = temperature
    if top_p is not None:
        override_config["topP"] = top_p

    async def generate():
        completion = client.create_prediction(
            PredictionData(
                chatflowId=chatflow_id,
                question=combined_prompt,
                streaming=True,
                overrideConfig=override_config
            )
        )

        chat_id = f"chatcmpl-{int(time.time())}"
        created_time = int(time.time())
        system_fingerprint = "fp_" + os.urandom(5).hex()
        yield f"data: {json.dumps({
                'id': chat_id,
                'object': 'chat.completion.chunk',
                'created': created_time,
                'model': chatflow_id,
                'system_fingerprint': system_fingerprint,
                'choices': [{
                    'index': 0,
                    'delta': {
                        'role': 'assistant',
                        'content': ''
                    },
                    'logprobs': None,
                    'finish_reason': None
                }]
            })}\n\n".encode('utf-8')


        for chunk in completion:
            try:
                chunk_data = json.loads(chunk)
                if "data" in chunk_data:
                    for data in chunk_data["data"]:
                        if isinstance(data, dict) and "messages" in data:
                            message = data["messages"][0] if data["messages"] else ""
                            response = {
                                "id": chat_id,
                                "object": "chat.completion.chunk",
                                "created": created_time,
                                "model": chatflow_id,
                                "system_fingerprint": system_fingerprint,
                                "choices": [{
                                    'index': 0,
                                    'delta': {
                                        'content': message
                                    },
                                    "logprobs": None,
                                    "finish_reason": None
                                }]
                            }
                            yield f"data: {json.dumps(response)}\n\n".encode('utf-8')
            except json.JSONDecodeError:
                yield f"data: {json.dumps({'error': f'Error decoding JSON from chunk: {chunk}'})}\n\n".encode('utf-8')
            
            await asyncio.sleep(0)

        yield f"data: {json.dumps({
            'id': chat_id,
            'object': 'chat.completion.chunk',
            'created': created_time,
            'model': chatflow_id,
            'system_fingerprint': system_fingerprint,
            'choices': [{
                'index': 0,
                'delta': {},
                'logprobs': None,
                'finish_reason': 'stop'
            }]
        })}\n\n".encode('utf-8')
    
        yield b"data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
