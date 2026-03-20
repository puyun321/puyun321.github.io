async function sendMessage() {
    const input = document.getElementById("user-input");
    const chatBox = document.getElementById("chat-box");

    const userText = input.value.trim();
    if (!userText) return;

    chatBox.innerHTML += `<div><b>你：</b>${userText}</div>`;
    input.value = "";

    const loadingId = "loading-" + Date.now();
    chatBox.innerHTML += `<div id="${loadingId}"><b>Bot：</b>思考中...</div>`;

    try {
        const response = await fetch("https://puyun321-github-io.onrender.com/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: userText })
        });

        const text = await response.text();
        console.log("Raw API回傳：", text);

        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            data = { reply: text };
        }

        document.getElementById(loadingId).remove();

        let reply = data.reply || data.response || "（無回應）";

        chatBox.innerHTML += `<div><b>Bot：</b>${reply}</div>`;
        chatBox.scrollTop = chatBox.scrollHeight;

    } catch (error) {
        document.getElementById(loadingId).remove();

        console.error("❌ fetch錯誤：", error);

        chatBox.innerHTML += `
            <div style="color:red;">
                <b>Bot：</b>連線失敗<br>
                <small>請確認 API 是否部署成功（Render）</small>
            </div>
        `;
    }
}