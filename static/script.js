const chatBox = document.getElementById("chatBox");
const input = document.getElementById("userInput");
const typing = document.getElementById("typing");

function addMessage(text, cls) {
    const div = document.createElement("div");
    div.className = "message " + cls;
    div.innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function showTyping(show) {
    typing.style.display = show ? "block" : "none";
}

function sendMessage(msgOverride=null) {
    const msg = msgOverride || input.value.trim();
    if (!msg) return;

    addMessage(msg, "user");
    input.value = "";
    showTyping(true);

    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ message: msg })
    })
    .then(res => res.json())
    .then(data => {
        showTyping(false);
        addMessage(data.reply, "bot");
    });
}

function sendCard(text) {
    sendMessage(text);
}

function resetChat() {
    fetch("/reset", { method: "POST" })
    .then(res => res.json())
    .then(data => {
        chatBox.innerHTML = "";
        addMessage(data.reply, "bot");
    });
}

function toggleTheme() {
    document.body.classList.toggle("light");
    document.body.classList.toggle("dark");
}

input.addEventListener("keydown", e => {
    if (e.key === "Enter") sendMessage();
});