from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, json, requests
from dotenv import load_dotenv
from langfuse import Langfuse

# ---------------- ENV ----------------
#load_dotenv()  # No need to override if .env is in the same folder
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path, override=True)
api_key = os.getenv("API_KEY")

print("OPENROUTER_API_KEY:", os.getenv("OPENROUTER_API_KEY"))


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

# ---------------- App ----------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Langfuse ----------------
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

# Tracks conversation per session
session_traces = {}

# ---------------- Default / Health ----------------
@app.get("/")
def root():
    return {"message": "Backend is running. Use /chat/stream to interact."}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# ---------------- Chat Route ----------------
@app.post("/chat/stream")
async def stream_chat(request: Request, x_session_id: str = Header(None), reset: bool = False):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")
       
    if not x_session_id:
        raise HTTPException(status_code=400, detail="Missing session ID")
    
    session_id = x_session_id
    if reset:
        session_traces.pop(session_id, None)

    # Get conversation from frontend
    data = await request.json()
    conversation = data.get("conversation", [])
    if not conversation and not reset:
        return JSONResponse({"error": "Empty conversation"})

    # Langfuse trace management
    trace_id = session_traces.get(session_id)
    if not trace_id:
        trace_id = langfuse.create_trace_id()
        session_traces[session_id] = trace_id

    # System prompt
    system_prompt = langfuse.get_prompt("system/default")
    system_content = getattr(system_prompt, "text", "You are a helpful assistant.")

    # Include full conversation (system + all user/assistant messages)
    messages = [{"role": "system", "content": system_content}]
    messages.extend(conversation)

    # Streaming response
    def event_stream():
        collected_output = ""
        try:
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": 200,
                "stream": True,
            }

            with requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, stream=True) as r:
                if r.status_code != 200:
                    print("OpenRouter error:", r.status_code, r.text)
                    yield f"data: {json.dumps({'content': '[Error: API request failed]'})}\n\n"
                    return

                for line in r.iter_lines():
                    if not line:
                        continue
                    decoded_line = line.decode("utf-8")
                    if decoded_line.startswith("data:"):
                        content = decoded_line[len("data:"):].strip()
                        if content == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            json_data = json.loads(content)
                            text = json_data["choices"][0]["delta"].get("content", "")
                            if text:
                                collected_output += text
                                yield f"data: {json.dumps({'content': text})}\n\n"
                        except Exception:
                            continue
        except Exception as e:
            yield f"data: {json.dumps({'content': '[Error: Streaming failed]'})}\n\n"
        finally:
            print(f"Trace ID: {trace_id}")
            print(f"Full conversation length: {len(conversation)}")
            print(f"Preview output: {collected_output[:200]}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
