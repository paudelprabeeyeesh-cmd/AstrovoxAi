import os
import openai
import requests
from PIL import Image
import pytesseract
import io


class VisionService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

    def analyze_image(self, image_url: str, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes images."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            max_tokens=500,
        )
        return response.choices[0].message.content or ""

    def extract_text_from_image(self, image_url: str) -> str:
        img_response = requests.get(image_url)
        img = Image.open(io.BytesIO(img_response.content))
        return pytesseract.image_to_string(img)

    def describe_image(self, image_url: str) -> str:
        return self.analyze_image(
            image_url, "Describe this image in detail. Include objects, colors, text, and context."
        )
