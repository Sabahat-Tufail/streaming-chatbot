const form = document.getElementById("chatForm");
const input = document.getElementById("userInput");
const chat = document.getElementById("chat");

form.addEventListener("submit", sendMessage);

async function sendMessage(event) {
    event.preventDefault();

    const userMessage = input.value.trim();
    if (!userMessage) return;

    chat.innerHTML += `<p><strong>User:</strong> ${userMessage}</p>`;
    input.value = "";

    const conversation = [{ role: "user", content: userMessage }];
    const assistantElem = document.createElement("p");
    assistantElem.innerHTML = "<strong>Assistant:</strong> ";
    chat.appendChild(assistantElem);

    const response = await fetch("http://127.0.0.1:8000/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });

        const lines = chunk.split("data:");
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed === "[DONE]") continue;

            try {
                const json = JSON.parse(trimmed);
                const delta = json.choices?.[0]?.delta?.content;
                if (delta) {
                    // Add gradual typing effect
                    for (const char of delta) {
                        assistantElem.innerHTML += char;
                        await delay(0); // 👈 small delay for visible chunking
                    }
                }
            } catch { }
        }
    }

    chat.scrollTop = chat.scrollHeight; // auto scroll
}

// helper function for delay
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
