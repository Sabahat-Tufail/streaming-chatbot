from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, json, requests
from dotenv import load_dotenv
from langfuse import Langfuse

# ---------------- ENV ----------------
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path, override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ---------------- App ----------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------------- Langfuse ----------------
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

# ---------------- OpenRouter ----------------
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

# ---------------- Trace storage ----------------
# Maps session ID -> Langfuse trace ID
session_traces = {}

# ---------------- Routes ----------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat/stream")
async def stream_chat(
    request: Request,
    x_session_id: str = Header(None),
    reset: bool = False
):
    if not x_session_id:
        raise HTTPException(status_code=400, detail="Missing session ID")

    session_id = x_session_id

    # ---------- Reset trace ----------
    if reset:
        session_traces.pop(session_id, None)

    # ---------- Extract conversation ----------
    data = await request.json()
    conversation = data if isinstance(data, list) else data.get("conversation", [])
    if not conversation and not reset:
        return {"error": "Empty conversation"}

    # ---------- Langfuse trace ----------
    if session_id in session_traces:
        trace_id = session_traces[session_id]
        print(f"Using existing Langfuse trace: {trace_id}")
    else:
        trace_id = langfuse.create_trace_id()
        session_traces[session_id] = trace_id
        print(f"Created new Langfuse trace: {trace_id}")

    # ---------- Last user message ----------
    user_input = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user" and msg.get("content"):
            user_input = msg["content"]
            break
    if not user_input and not reset:
        return {"error": "No valid user message found"}

    # ---------- System prompt ----------
    system_prompt = langfuse.get_prompt("system/default")
    system_content = getattr(system_prompt, "text", "You are a helpful assistant.")

    # ---------- Streaming Response ----------
    def event_stream():
        collected_output = ""
        try:
            payload = {
                "model": "meta-llama/llama-3.1-70b-instruct",
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_input}
                ],
                "max_tokens": 200,
                "stream": True,
            }

            with requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, stream=True) as r:
                for line in r.iter_lines():
                    if line:
                        decoded_line = line.decode("utf-8")
                        if decoded_line.startswith("data:"):
                            data_str = decoded_line[len("data:"):].strip()
                            if data_str == "[DONE]":
                                yield "data: [DONE]\n\n"
                                break
                            try:
                                json_data = json.loads(data_str)
                                text = json_data["choices"][0]["delta"].get("content", "")
                                if text:
                                    collected_output += text
                                    yield f"data: {json.dumps({'content': text})}\n\n"
                            except:
                                continue
        except GeneratorExit:
            # Client disconnected; ignore generator exit
            pass
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Log trace and conversation info
            print(f"Trace ID: {trace_id}")
            print(f"User Input: {user_input}")
            print(f"Model Output (truncated): {collected_output[:300]}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
