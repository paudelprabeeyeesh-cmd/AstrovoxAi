import sys
import requests

API_URL = "http://127.0.0.1:8000/stream/"

def launch_dashboard():
    print("=================================================================")
    print("🌐 Astravox NETWORK CLIENT INTERFACE — ONLINE")
    print(f"Connecting to Core API Gateway at {API_URL.replace('stream/', '')}")
    print("=================================================================")

    while True:
        try:
            user_input = input("\n👤 You: ")
            if user_input.lower() in ['exit', 'quit']:
                print("\nDisconnecting from Astravox Gateway. Goodbye!")
                break
            if not user_input.strip():
                continue

            payload = {
                "user": "Prabeyesh",
                "prompt": user_input,
                "context_scope": "Architecture Development"
            }

            print("🤖 Astravox: ", end="", flush=True)

            # Fire HTTP POST request with network stream monitoring enabled
            response = requests.post(API_URL, json=payload, stream=True)
            
            if response.status_code != 200:
                print(f"\n⚠️ Network Error: Unable to reach engine (Status {response.status_code})")
                continue

            try:
                # Intercept incoming server data chunks
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8').strip()
                        # Parse SSE format standard
                        if decoded_line.startswith("data: "):
                            print(decoded_line[6:], end="", flush=True)
                        # Fallback for raw text blocks
                        elif decoded_line:
                            print(decoded_line, end="", flush=True)
            except requests.exceptions.StreamConsumedError:
                # Stream parsed immediately backup handler
                raw_text = response.text.replace("data: ", "").strip()
                if raw_text:
                    print(raw_text, end="", flush=True)
            
            print()  # Inserts clean line breaks after the generation stream wraps up

        except KeyboardInterrupt:
            print("\n\nSession terminated by user. Shutting down UI layers.")
            break
        except requests.exceptions.ConnectionError:
            print("\n\n⚠️ Connection Error: Is the API server running on port 8000?")
            break

if __name__ == "__main__":
    launch_dashboard()