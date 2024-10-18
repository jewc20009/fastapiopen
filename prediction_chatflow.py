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
            chatflowId="5a5f2611-1514-488c-980b-87c5a6ecc906",
            question="Que hora es?",
            streaming=True,
            overrideConfig={"SessionId": "253ed250-64fe-4f5d-af87-0720348f7957"}
        )
    )

   
    # Process and print each streamed chunk
    print("Streaming response:")
    for chunk in completion:
        # {event: "token", data: "hello"}
        print(chunk)


if __name__ == "__main__":
    test_streaming()
