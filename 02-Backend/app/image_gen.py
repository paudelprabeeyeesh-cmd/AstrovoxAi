import os
import io
import openai
import requests
from typing import Optional


class ImageGenerator:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

    def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            n=1,
        )
        return response.data[0].url

    def edit_image(self, image_url: str, prompt: str) -> str:
        img_response = requests.get(image_url)
        img_file = io.BytesIO(img_response.content)
        img_file.name = "image.png"
        response = self.client.images.edit(
            model="dall-e-2",
            image=img_file,
            prompt=prompt,
            n=1,
            size="1024x1024",
        )
        return response.data[0].url
