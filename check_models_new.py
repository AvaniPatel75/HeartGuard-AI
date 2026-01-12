from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
print(f"Key found: {api_key[:5]}...")

try:
    client = genai.Client(api_key=api_key)
    print("Listing models with google-genai SDK:")
    pager = client.models.list()
    # The return type might be an iterator or pager, let's try to iterate
    for model in pager:
        print(f"- {model.name}")
except Exception as e:
    print(f"Error listing models: {e}")
