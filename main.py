from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static and template files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/chat/stream")
async def stream_chat(request: Request):
    data = await request.json()
    conversation = data.get("conversation", [])

    # Make sure the API key exists
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return {"error": "Missing API key"}

    # Create OpenRouter streaming request
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-3.5-turbo",
            "stream": True,
            "messages": conversation,
        },
        stream=True,
    )

    def event_stream():
        try:
            for chunk in response.iter_lines(decode_unicode=True):
                if chunk:
                    # Stop when OpenRouter sends [DONE]
                    if chunk.strip() == "data: [DONE]":
                        yield "data: [DONE]\n\n"
                        break
                    yield f"{chunk}\n"
        finally:
            response.close()  # ✅ make sure connection closes cleanly

    return StreamingResponse(event_stream(), media_type="text/event-stream")
