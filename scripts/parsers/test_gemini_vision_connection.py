import os
import sys
from dotenv import load_dotenv
from google import genai

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
api_key = os.getenv("GEMINI_API_KEYS")

client = genai.Client(api_key=api_key)

print(f"[+] Testing model='gemini-3.6-flash' with user syntax...")

try:
    if hasattr(client, 'interactions'):
        interaction = client.interactions.create(
            model="gemini-3.6-flash",
            input="Hello! State 'Gemini 3.6 Flash Active'."
        )
        print(f"[+] Result via client.interactions: {interaction.output_text}")
    else:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents="Hello! State 'Gemini 3.6 Flash Active'."
        )
        print(f"[+] Result via client.models: {response.text}")
except Exception as e:
    print(f"[!] Error with gemini-3.6-flash: {e}")
