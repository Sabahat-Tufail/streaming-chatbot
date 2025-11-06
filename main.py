from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, json
from dotenv import load_dotenv
from langfuse import Langfuse
from groq import Groq

# ------------------ ENV SETUP ------------------
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path, override=True)

print("Loaded Groq Key:", os.getenv("GROQ_API_KEY"))
print("Loaded Langfuse Public Key:", os.getenv("LANGFUSE_PUBLIC_KEY"))

app = FastAPI()

# ------------------ CORS ------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Static + Templates ------------------
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ------------------ Langfuse ------------------
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

# ------------------ Groq Client ------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise Exception("Please set GROQ_API_KEY in environment variables")

groq_client = Groq(api_key=GROQ_API_KEY)

# ------------------ Routes ------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/chat/stream")
async def stream_chat(request: Request):
    data = await request.json()
    conversation = data if isinstance(data, list) else data.get("conversation", [])

    if not conversation:
        return {"error": "Empty conversation"}

    trace_id = langfuse.create_trace_id()
    print(f"Langfuse trace started: {trace_id}")

    # Use only the latest valid user message
    user_input = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user" and msg.get("content"):
            user_input = msg["content"]
            break

    if not user_input:
        return {"error": "No valid user message found"}

    # ------------------ Streaming Generator ------------------
    def event_stream():
        collected_output = ""
        try:
            # Groq chat completion (non-blocking, simple streaming)
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": user_input}
                ],
                model="llama‑3.3‑70b‑versatile",
                stream=True
            )

            for chunk in response:
                if hasattr(chunk, "choices"):
                    text_chunk = chunk.choices[0].delta.get("content", "")
                    if text_chunk:
                        collected_output += text_chunk
                        yield f"data: {json.dumps({'content': text_chunk})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            print("\n--- Langfuse Trace Log ---")
            print(f"Trace ID: {trace_id}")
            print(f"User Input: {user_input}")
            print(f"Model Output (truncated): {collected_output[:300]}")
            print("---------------------------\n")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
