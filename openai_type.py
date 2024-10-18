from flowise import Flowise, PredictionData
import json
import os
from dotenv import load_dotenv
import time

load_dotenv()

def test_streaming():
    client = Flowise(base_url=os.getenv("BASE_URL"), api_key=os.getenv("JWT"))

    # Test streaming prediction
    completion = client.create_prediction(
        PredictionData(
            chatflowId="680b56dd-7183-418a-b36a-7219d4646bf1",
            question="busca las noticias!",
            streaming=True,
            overrideConfig={"SessionId": "680b56dd-7183-418a-b36a-7219d4646bf1"}
        )
    )

    # Process and print each streamed chunk in OpenAI-like format
    print("Streaming response:")
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
                            "model": "flowise-680b56dd-7183-418a-b36a-7219d4646bf1",
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
                        print(json.dumps(response))
                        print()
        except json.JSONDecodeError:
            print(f"Error decoding JSON from chunk: {chunk}")

    # Send the final message to indicate completion
    final_response = {
        "id": f"chatcmpl-{time.time()}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "flowise-680b56dd-7183-418a-b36a-7219d4646bf1",
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }
        ]
    }
    print(json.dumps(final_response))

if __name__ == "__main__":
    test_streaming()