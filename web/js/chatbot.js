const $ = (id) => document.getElementById(id);

if (!AsisVoz.isReady()) {
  window.location.href = "./configurar.html";
}

const chatBox = $("chatBox");
const chatInput = $("chatInput");
const sendBtn = $("sendBtn");
const chatStatus = $("chatStatus");
const modelInput = $("modelInput");
const clearChatBtn = $("clearChatBtn");

function getHistory() {
  const data = AsisVoz.getJson(AsisVoz.STORAGE_KEYS.chatHistory, []);
  return Array.isArray(data) ? data : [];
}

function saveHistory(items) {
  AsisVoz.setJson(AsisVoz.STORAGE_KEYS.chatHistory, items.slice(-30));
}

function renderHistory() {
  const history = getHistory();
  chatBox.innerHTML = "";
  if (!history.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Sin mensajes aun.";
    chatBox.appendChild(empty);
    return;
  }

  history.forEach((m) => {
    const bubble = document.createElement("div");
    bubble.className = `bubble ${m.role === "user" ? "bubble-user" : "bubble-assistant"}`;
    bubble.textContent = m.content;
    chatBox.appendChild(bubble);
  });
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
  const content = chatInput.value.trim();
  if (!content) return;

  const openrouterKey = AsisVoz.get(AsisVoz.STORAGE_KEYS.openrouterKey);
  const model = modelInput.value.trim() || "openai/gpt-4o-mini";
  const history = getHistory();
  history.push({ role: "user", content });
  saveHistory(history);
  renderHistory();
  chatInput.value = "";

  sendBtn.disabled = true;
  AsisVoz.setStatus(chatStatus, "Consultando modelo...", true);
  try {
    const text = await AsisVoz.chatCompletion(openrouterKey, model, history);
    const next = getHistory();
    next.push({ role: "assistant", content: text });
    saveHistory(next);
    renderHistory();
    AsisVoz.setStatus(chatStatus, "Respuesta recibida.", true);
  } catch (err) {
    AsisVoz.setStatus(chatStatus, err.message || "No se pudo obtener respuesta.", false);
  } finally {
    sendBtn.disabled = false;
  }
}

sendBtn.addEventListener("click", sendMessage);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});
clearChatBtn.addEventListener("click", () => {
  AsisVoz.setJson(AsisVoz.STORAGE_KEYS.chatHistory, []);
  renderHistory();
});

renderHistory();
