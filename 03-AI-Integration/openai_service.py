import os
from openai import OpenAI
from dotenv import load_dotenv  # 1. Add this line

load_dotenv()  # 2. Add this line to load your hidden .env file

# This will now successfully grab your real key from the .env file!
client = OpenAI(api_key=os.getenv("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 "))

def get_astrovox_response(user_message: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Astrovox AI, an advanced assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Backend AI Error: {str(e)}"