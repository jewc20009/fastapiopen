from flowise import Flowise, PredictionData
import json
import os
from dotenv import load_dotenv

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

    # Process and print each streamed chunk
    print("Streaming response:")
    for chunk in completion:
        print(chunk)
        try:
            # Extract the message and used tools from the chunk
            if isinstance(chunk, str):
                chunk_data = json.loads(chunk)
                if "data" in chunk_data:
                    for data in chunk_data["data"]:
                        if isinstance(data, dict):
                            message = data.get("messages", [])[0] if isinstance(data.get("messages"), list) and data.get("messages") else None
                            used_tools = data.get("usedTools", [])
                            
                            if message:
                                print("Message:", message)
                            if used_tools:
                                print("Used Tools:", used_tools)
        except json.JSONDecodeError:
            print("Error decoding JSON from chunk:", chunk)

if __name__ == "__main__":
    test_streaming()
    