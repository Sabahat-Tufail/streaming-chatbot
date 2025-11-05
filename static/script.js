// ----- State -----
let conversation = JSON.parse(localStorage.getItem("chatHistory") || "[]");

const chatBox = document.getElementById("chat");
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");

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

    // Add empty assistant message container
    const assistantDiv = document.createElement("div");
    assistantDiv.classList.add("message", "assistant");
    chatBox.appendChild(assistantDiv);

    try {
        // Send POST request to backend
        const response = await fetch("http://127.0.0.1:8000/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(conversation),
        });

        if (!response.ok) {
            assistantDiv.textContent = "[Error: " + response.status + "]";
            return;
        }

        // Handle streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantText = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });

            // Split into lines and process each 'data:' line
            const lines = chunk.split("\n").filter(line => line.trim().startsWith("data:"));
            for (const line of lines) {
                const data = line.replace("data: ", "").trim();
                if (data === "[DONE]") break;

                try {
                    const json = JSON.parse(data);
                    const delta = json.choices?.[0]?.delta?.content || "";
                    assistantText += delta;
                    assistantDiv.textContent = assistantText;
                    chatBox.scrollTop = chatBox.scrollHeight;
                } catch (e) {
                    console.warn("Skipping invalid chunk:", data);
                }
            }
        }

        // Save assistant's complete response
        conversation.push({ role: "assistant", content: assistantText });
        saveChat();
        renderChat();
    } catch (err) {
        console.error("Error:", err);
        assistantDiv.textContent = "[Network error]";
    }
}

// ----- Init -----
chatForm.addEventListener("submit", sendMessage);
renderChat();
