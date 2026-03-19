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

    try {
        const response = await fetch("http://127.0.0.1:8000/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: userText })
        });

        // ⭐ 先拿純文字（避免 JSON crash）
        const text = await response.text();
        console.log("Raw API回傳：", text);

        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            console.warn("⚠️ 回傳不是JSON，直接當文字處理");
            data = { reply: text };
        }

        document.getElementById(loadingId).remove();

        // ⭐ 容錯處理
        let reply = "（無回應）";

        if (data.reply) {
            reply = data.reply;
        } else if (data.response) {
            reply = data.response;
        } else if (typeof data === "string") {
            reply = data;
        }

        chatBox.innerHTML += `<div><b>Bot：</b>${reply}</div>`;
        chatBox.scrollTop = chatBox.scrollHeight;

    } catch (error) {
        document.getElementById(loadingId).remove();

        console.error("❌ fetch錯誤：", error);

        chatBox.innerHTML += `
            <div style="color:red;">
                <b>Bot：</b>連線失敗<br>
                <small>請確認 Flask server 是否開啟 / CORS 是否設定</small>
            </div>
        `;
    }
}