# FastAPI Chatbot

This repository provides a **real-time streaming chatbot** using **FastAPI** for the backend and a simple **HTML/CSS/JS frontend**. The AI backend uses **OpenRouter AI** (`gpt-3.5-turbo`) and **Langfuse** for trace management and session-based conversation tracking.

**Security:** The backend now requires an **API key** for authentication.

---

## Features

* Real-time **chat streaming** via FastAPI and **Server-Sent Events (SSE)**.
* Full conversation handling per session.
* Conversation **history saved locally** in the browser.
* **Session reset** functionality.
* **API key authentication** for secure backend access.
* Clean, responsive **frontend** built with HTML/CSS/JS.
* **Health check endpoint** for monitoring the backend.

---

## 1️⃣ Backend (FastAPI)

Your `main.py` serves **only the API**, no frontend files.

### Requirements

* Python 3.10+
* Packages:

```bash
pip install fastapi uvicorn python-dotenv requests langfuse
```

### Environment Variables

Create a `.env` file in the project root:

```env
API_KEY=<your-secret-api-key>                # required for backend authentication
OPENROUTER_API_KEY=<your_openrouter_api_key>
LANGFUSE_PUBLIC_KEY=<your_langfuse_public_key>
LANGFUSE_SECRET_KEY=<your_langfuse_secret_key>
LANGFUSE_HOST=<optional_langfuse_host_url>
```

> ⚠️ The `API_KEY` is **used to authenticate requests** from your frontend to the backend.

---

### Running the Backend

```bash
cd C:\Users\DELL\Downloads\streaming-chatbot-main\streaming-chatbot-main
uvicorn main:app --reload
```

Backend will now be available at:

```
http://127.0.0.1:8000
```

Check health endpoint:

```
http://127.0.0.1:8000/health
```

It should return:

```json
{"status":"ok"}
```

---

### Chat Streaming Endpoint

* `POST /chat/stream`

* Headers:

  * `x-session-id`: unique session ID per browser
  * `x-api-key`: your secret API key from `.env`
  * `reset` (optional): `true/false` to reset conversation

* Body example:

```json
{
  "conversation": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help you?"}
  ]
}
```

* Streams AI response back via SSE.
* Handles full conversation history per session.
* Supports session reset using `reset=true`.
* Only allows requests with the correct **API key**.

---

## 2️⃣ Frontend (HTML/JS)

The frontend is **served separately** via a static file server.

### Folder Structure

```
frontend/
├─ templates/
│  └─ index.html
├─ static/
│  ├─ style.css
│  └─ script.js
```

### Serve Frontend Locally

Use Python’s simple HTTP server:

```bash
cd C:\Users\DELL\Downloads\streaming-chatbot-main
python -m http.server 5500
```

Open in browser:

```
http://127.0.0.1:5500/templates/index.html
```

### Frontend Integration with API Key

Update your `script.js` to **send the API key** with every request:

```js
const API_KEY = "<your-secret-api-key>"; // same as in .env

const response = await fetch("http://127.0.0.1:8000/chat/stream", {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "x-session-id": sessionId,
        "x-api-key": API_KEY
    },
    body: JSON.stringify({ conversation })
});
```

> ⚠️ Make sure the key here matches the one in your backend `.env`.

---

### Important Notes

* Make sure all paths to static files in `index.html` are correct:

```html
<link rel="stylesheet" href="/static/style.css">
<script src="/static/script.js"></script>
```

* Frontend uses **`x-session-id`** to maintain session-based conversation.
* The **🗑️ New Chat** button resets both frontend local storage and backend session trace.
* Make sure **backend (`main.py`) and frontend** are running simultaneously for the chat to work.

---

## Frontend Features

* **Chat container** scrolls automatically as messages appear.
* **User messages** in blue, **assistant messages** in gray.
* **Responsive design** (works on desktop and mobile).
* **Local storage** preserves chat history.
* **Session ID per browser** ensures persistent conversation tracking.



