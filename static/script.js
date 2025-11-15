// ----- State -----
let conversation = JSON.parse(localStorage.getItem("chatHistory") || "[]");

// Generate or reuse session ID per browser
let sessionId = localStorage.getItem("sessionId");
if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem("sessionId", sessionId);
}

const chatBox = document.getElementById("chat");
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");
const clearChat = document.getElementById("clearChat");

// ----- Render Chat -----
function renderChat() {
    chatBox.innerHTML = "";
    conversation.forEach(msg => {
        const div = document.createElement("div");
        div.classList.add("message", msg.role);
        div.textContent = msg.content;
        chatBox.appendChild(div);
    });
    chatBox.scrollTop = chatBox.scrollHeight;
}

// ----- Save Chat -----
function saveChat() {
    localStorage.setItem("chatHistory", JSON.stringify(conversation));
}

// ----- Send Message -----
async function sendMessage(event) {
    event.preventDefault();
    const text = userInput.value.trim();
    if (!text) return;

    // Add user message
    conversation.push({ role: "user", content: text });
    saveChat();
    renderChat();
    userInput.value = "";

    // Create assistant message placeholder
    const assistantDiv = document.createElement("div");
    assistantDiv.classList.add("message", "assistant");
    assistantDiv.textContent = "";
    chatBox.appendChild(assistantDiv);

    try {
        console.log("Sending conversation:", conversation);

        const response = await fetch("http://127.0.0.1:8000/chat/stream", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-session-id": sessionId,
                "x-api-key": "mysecret123"

            },
            body: JSON.stringify({ conversation })
        });


        if (!response.ok) {
            assistantDiv.textContent = `[Error: ${response.status}]`;
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantText = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split("\n").filter(line => line.startsWith("data: "));

            for (const line of lines) {
                const data = line.replace("data: ", "").trim();
                if (data === "[DONE]") continue;

                try {
                    const json = JSON.parse(data);
                    const delta = json.content || "";
                    if (delta) {
                        assistantText += delta;
                        assistantDiv.textContent = assistantText;
                        chatBox.scrollTop = chatBox.scrollHeight;
                    }
                } catch {
                    // ignore incomplete chunks
                }
            }
        }

        // Save assistant response
        conversation.push({ role: "assistant", content: assistantText });
        saveChat();
        renderChat();
    } catch (err) {
        console.error("Network Error:", err);
        assistantDiv.textContent = "[Network error]";
    }
}

// ----- Clear Chat -----
clearChat.addEventListener("click", async () => {
    if (confirm("Are you sure you want to delete this conversation?")) {
        localStorage.removeItem("chatHistory");

        // Reset trace on backend
        try {
            await fetch("http://127.0.0.1:8000/chat/stream?reset=true", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "x-session-id": sessionId
                },
                body: JSON.stringify({ conversation: [] })
            });
        } catch {
            // ignore
        }

        location.reload();
    }
});

// ----- Init -----
chatForm.addEventListener("submit", sendMessage);
renderChat();
