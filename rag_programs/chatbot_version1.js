async function sendMessage() {
    const input = document.getElementById("user-input");
    const chatBox = document.getElementById("chat-box");

    const userText = input.value.trim();
    if (!userText) return;

    // 顯示使用者訊息
    chatBox.innerHTML += `<div><b>你：</b>${userText}</div>`;
    input.value = "";

    // loading
    const loadingId = "loading-" + Date.now();
    chatBox.innerHTML += `<div id="${loadingId}"><b>Bot：</b>思考中...</div>`;
    chatBox.scrollTop = chatBox.scrollHeight;

    // 🔥 自動切換 API（本地 / Render）
    const API_URL = location.hostname === "localhost" || location.hostname === "127.0.0.1"
        ? "http://127.0.0.1:8000/chat"
        : "https://puyun321-github-io.onrender.com/chat";

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: userText })
        });

        // 🔥 有些後端會回文字不是JSON
        const text = await response.text();
        console.log("Raw API回傳：", text);

        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            data = { reply: text };
        }

        document.getElementById(loadingId).remove();

        // 🔥 多種格式容錯
        let reply = "（無回應）";

        if (data.reply && data.reply.trim() !== "") {
            reply = data.reply;
        } else if (data.response && data.response.trim() !== "") {
            reply = data.response;
        } else if (typeof data === "string") {
            reply = data;
        }

        // 🔴 避免顯示錯誤訊息
        if (reply.includes("HF錯誤") || reply.includes("ERROR")) {
            reply = "目前模型服務不穩定，已改用備用回答";
        }

        chatBox.innerHTML += `<div><b>Bot：</b>${reply}</div>`;
        chatBox.scrollTop = chatBox.scrollHeight;

    } catch (error) {
        document.getElementById(loadingId).remove();

        console.error("❌ fetch錯誤：", error);

        chatBox.innerHTML += `
            <div style="color:red;">
                <b>Bot：</b>連線失敗<br>
                <small>請確認後端 API 是否啟動（Render 或本地）</small>
            </div>
        `;
    }
}