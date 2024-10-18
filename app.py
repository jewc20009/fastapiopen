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

client = Flowise(base_url="https://flowise-liy3.onrender.com", api_key="8NV4sPvewPTEBCl3KxOwpFsniEiXS0Ex6TCKpxKbFuQ")

@app.post("/v1/chat/completions")
async def chat(request: Request, authorization: str = Header(None)):
    if not authorization.startswith("Bearer "):
        return {"error": "Invalid Authorization header"}
    
    session_id = authorization.split("Bearer ")[1]  # Using the API key as session_id
    
    data = await request.json()
    chatflow_id = data.get('model', '')  # Using the 'model' as chatflow_id
    messages = data.get('messages', [])
    stream = data.get('stream', False)

    # Additional OpenAI parameters (some will be ignored for Flowise)
    max_tokens = data.get('max_tokens')
    temperature = data.get('temperature')
    top_p = data.get('top_p')
    n = data.get('n')
    stop = data.get('stop')
    presence_penalty = data.get('presence_penalty')
    frequency_penalty = data.get('frequency_penalty')
    logit_bias = data.get('logit_bias')
    user = data.get('user')

    if not stream:
        return {"error": "Only streaming responses are supported"}

    # Combine system and user messages into one prompt for Flowise
    system_message = next((msg['content'] for msg in messages if msg['role'] == 'system'), "")
    user_messages = [msg['content'] for msg in messages if msg['role'] == 'user']
    
    combined_prompt = f"{system_message}\n\n" + "\n".join(user_messages)

    # Prepare override config
    override_config = {
        "sessionId": session_id,
        "chatHistory": messages,  # Passing full message history
    }

    # Add OpenAI parameters to override_config if they are present
    if max_tokens is not None:
        override_config["maxTokens"] = max_tokens
    if temperature is not None:
        override_config["temperature"] = temperature
    if top_p is not None:
        override_config["topP"] = top_p
    # Note: n, stop, presence_penalty, frequency_penalty, logit_bias are not typically used in Flowise
    # but you could add them to override_config if Flowise supports them

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

        # Send initial message
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
                    'content': '',
                    'refusal': None
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
                                'id': chat_id,
                                'object': 'chat.completion.chunk',
                                'created': created_time,
                                'model': chatflow_id,
                                'system_fingerprint': system_fingerprint,
                                'choices': [{
                                    'index': 0,
                                    'delta': {
                                        'content': message
                                    },
                                    'logprobs': None,
                                    'finish_reason': None
                                }]
                            }
                            yield f"data: {json.dumps(response)}\n\n".encode('utf-8')
            except json.JSONDecodeError:
                yield f"data: {json.dumps({'error': f'Error decoding JSON from chunk: {chunk}'})}\n\n".encode('utf-8')
            
            await asyncio.sleep(0)  # Allow other tasks to run

        # Send the final message to indicate completion
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

        # Send [DONE] message
        yield b"data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)