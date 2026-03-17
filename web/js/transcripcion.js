const $ = (id) => document.getElementById(id);

if (!AsisVoz.isReady()) {
  window.location.href = "./configurar.html";
}

const audioInput = $("audioInput");
const transcribeBtn = $("transcribeBtn");
const balanceBtn = $("balanceBtn");
const balanceText = $("balanceText");
const transcribeStatus = $("transcribeStatus");
const historyList = $("historyList");
const downloadLink = $("downloadLink");

function getHistory() {
  const data = AsisVoz.getJson(AsisVoz.STORAGE_KEYS.history, []);
  return Array.isArray(data) ? data : [];
}

function saveHistory(items) {
  AsisVoz.setJson(AsisVoz.STORAGE_KEYS.history, items.slice(0, 50));
}

function pushHistory(entry) {
  const current = getHistory();
  current.unshift(entry);
  saveHistory(current);
}

function renderHistory() {
  const items = getHistory();
  historyList.innerHTML = "";
  if (!items.length) {
    historyList.innerHTML = "<li>Sin historial todavia.</li>";
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    const label = document.createElement("div");
    const ts = new Date(item.createdAt).toLocaleString();
    label.textContent = `${item.fileName} - ${ts}`;

    const btn = document.createElement("button");
    btn.className = "ghost";
    btn.textContent = "Descargar";
    btn.addEventListener("click", async () => {
      await AsisVoz.generateDocx(item.fileName, item.lines, item.sourceName);
    });

    li.appendChild(label);
    li.appendChild(btn);
    historyList.appendChild(li);
  });
}

balanceBtn.addEventListener("click", async () => {
  const deepgramKey = AsisVoz.get(AsisVoz.STORAGE_KEYS.deepgramKey);
  balanceBtn.disabled = true;
  balanceText.textContent = "Consultando saldo...";
  try {
    const balance = await AsisVoz.deepgramBalance(deepgramKey);
    balanceText.textContent = `Saldo: ${balance}`;
  } catch (err) {
    balanceText.textContent = `Saldo: ${err.message || "No disponible"}`;
  } finally {
    balanceBtn.disabled = false;
  }
});

transcribeBtn.addEventListener("click", async () => {
  const deepgramKey = AsisVoz.get(AsisVoz.STORAGE_KEYS.deepgramKey);
  const file = audioInput.files?.[0];
  if (!file) {
    AsisVoz.setStatus(transcribeStatus, "Selecciona un archivo.", false);
    return;
  }

  transcribeBtn.disabled = true;
  downloadLink.classList.add("hidden");
  AsisVoz.setStatus(transcribeStatus, "Transcribiendo...", true);

  try {
    const res = await AsisVoz.transcribeFile(file, deepgramKey);
    const lines = AsisVoz.buildTranscriptLines(res);
    const docxName = `${AsisVoz.sanitizeFilename(file.name)}.docx`;
    await AsisVoz.generateDocx(docxName, lines, file.name);

    pushHistory({
      fileName: docxName,
      sourceName: file.name,
      createdAt: new Date().toISOString(),
      lines,
    });
    renderHistory();

    AsisVoz.setStatus(transcribeStatus, `Listo: ${docxName}`, true);
    downloadLink.classList.remove("hidden");
    downloadLink.onclick = async (e) => {
      e.preventDefault();
      await AsisVoz.generateDocx(docxName, lines, file.name);
    };
  } catch (err) {
    AsisVoz.setStatus(transcribeStatus, err.message || "No se pudo transcribir.", false);
  } finally {
    transcribeBtn.disabled = false;
  }
});

renderHistory();
