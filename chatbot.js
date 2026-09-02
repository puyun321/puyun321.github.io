const API_URL = "https://puyun321-github-io.onrender.com/chat";

// running conversation, sent back to the API so follow-up questions have context
const history = [];

const SUGGESTIONS = [
    "What are Pu Yun's main research areas?",
    "Which of his projects do you find most interesting?",
    "Tell me about his latest publication",
    "What awards has he received?"
];

function toggleChat() {
    const container = document.getElementById("chat-container");
    const btn = document.getElementById("chat-toggle-btn");
    container.classList.toggle("hidden");
    const open = !container.classList.contains("hidden");
    btn.textContent = open ? "✕" : "💬";
    if (open) {
        const box = document.getElementById("chat-box");
        if (box && box.children.length === 0) showWelcome();
        const input = document.getElementById("user-input");
        if (input) input.focus();
    }
}

function showWelcome() {
    appendMsg(
        "Hi! I'm Pu Yun's assistant. Ask me about his research, projects, or " +
        "which of his work you might find most interesting.",
        "msg-bot"
    );
    const chatBox = document.getElementById("chat-box");
    const wrap = document.createElement("div");
    wrap.className = "msg-suggestions";
    SUGGESTIONS.forEach((s) => {
        const b = document.createElement("button");
        b.className = "suggestion-chip";
        b.textContent = s;
        b.onclick = () => {
            const input = document.getElementById("user-input");
            input.value = s;
            sendMessage();
        };
        wrap.appendChild(b);
    });
    chatBox.appendChild(wrap);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// tiny markdown renderer: bold, italic, and bullet / numbered lists
function renderMarkdown(text) {
    const html = escapeHtml(text)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/(^|[^*])\*(?!\s)([^*\n]+?)\*(?!\*)/g, "$1<em>$2</em>");

    const lines = html.split("\n");
    let out = "";
    let inList = false;
    for (const ln of lines) {
        const m = ln.match(/^\s*(?:[-*•]|\d+\.)\s+(.*)$/);
        if (m) {
            if (!inList) { out += "<ul>"; inList = true; }
            out += "<li>" + m[1] + "</li>";
        } else {
            if (inList) { out += "</ul>"; inList = false; }
            if (ln.trim()) out += "<p>" + ln + "</p>";
        }
    }
    if (inList) out += "</ul>";
    return out || escapeHtml(text);
}

function appendMsg(text, type) {
    const chatBox = document.getElementById("chat-box");
    const div = document.createElement("div");
    div.className = type;
    if (type === "msg-bot") {
        div.innerHTML = renderMarkdown(text);
    } else {
        div.textContent = text;
    }
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    return div;
}

async function sendMessage() {
    const input = document.getElementById("user-input");
    const userText = input.value.trim();
    if (!userText) return;

    const sugg = document.querySelector(".msg-suggestions");
    if (sugg) sugg.remove();

    appendMsg(userText, "msg-user");
    input.value = "";

    const loading = appendMsg("思考中...", "msg-bot msg-loading");

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: userText,
                history: history.slice(-8)   // prior turns only
            })
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

        history.push({ role: "user", content: userText });
        history.push({ role: "assistant", content: reply });

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
