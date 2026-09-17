import pathlib

main_path = pathlib.Path(r'C:\AstrovoxAi\02-Backend\app\main.py')
content = main_path.read_text()

chat_part = content.split("async def ws_chat")[1].split("async def ws_voice")[0]
voice_part = content.split("async def ws_voice")[1]

print("ws_chat has router.record:", "router.record(model.model_id" in chat_part)
print("ws_chat has SSE parsing:", 'line.startswith("data:")' in chat_part)
print("ws_chat has clean JSON:", 'send_json({"type": "token"' in chat_part)
print("ws_voice has router.record:", "router.record(model.model_id" in voice_part)
print("ws_voice has SSE parsing:", 'line.startswith("data:")' in voice_part)
print("ws_voice has clean JSON:", 'send_json({"type": "token"' in voice_part)
