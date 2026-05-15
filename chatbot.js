function toggleChat() {
    const container = document.getElementById("chat-container");
    const btn = document.getElementById("chat-toggle-btn");
    container.classList.toggle("hidden");
    btn.textContent = container.classList.contains("hidden") ? "💬" : "✕";
}

function appendMsg(text, type) {
    const chatBox = document.getElementById("chat-box");
    const div = document.createElement("div");
    div.className = type;
    div.textContent = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    return div;
}

async function sendMessage() {
    const input = document.getElementById("user-input");
    const userText = input.value.trim();
    if (!userText) return;

    appendMsg(userText, "msg-user");
    input.value = "";

    const loading = appendMsg("思考中...", "msg-bot msg-loading");

    const API_URL = "https://puyun321-github-io.onrender.com/chat";

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: userText })
        });

        const text = await response.text();
        let data;
        try { data = JSON.parse(text); } catch (e) { data = { reply: text }; }

        loading.remove();

        let reply = "（無回應）";
        if (data.reply && data.reply.trim() !== "") {
            reply = data.reply;
        } else if (data.response && data.response.trim() !== "") {
            reply = data.response;
        } else if (typeof data === "string" && data.trim() !== "") {
            reply = data;
        }

        appendMsg(reply, "msg-bot");

    } catch (error) {
        loading.remove();
        const div = appendMsg("連線失敗，請確認 API 是否啟動。", "msg-bot");
        div.style.color = "#ef4444";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("user-input");
    if (input) {
        input.addEventListener("keypress", (e) => {
            if (e.key === "Enter") sendMessage();
        });
    }
});
