const $ = (id) => document.getElementById(id);

if (!AsisVoz.isReady()) {
  window.location.href = "./configurar.html";
}

const tabTranscriptor = $("tabTranscriptor");
const tabChatbot = $("tabChatbot");
const panelTranscriptor = $("panelTranscriptor");
const panelChatbot = $("panelChatbot");

const audioInput = $("audioInput");
const clearFileBtn = $("clearFileBtn");
const selectedFileName = $("selectedFileName");
const transcribeBtn = $("transcribeBtn");
const transcribeStatus = $("transcribeStatus");
const historyList = $("historyList");
const transcribeLoader = $("transcribeLoader");

const balancePill = $("balancePill");
const themeToggle = $("themeToggle");

const modelSelect = $("modelSelect");
const reloadModelsBtn = $("reloadModelsBtn");
const chatBox = $("chatBox");
const chatInput = $("chatInput");
const sendBtn = $("sendBtn");
const chatStatus = $("chatStatus");
const clearChatBtn = $("clearChatBtn");
const chatFileInput = $("chatFileInput");
const clearChatFileBtn = $("clearChatFileBtn");
const chatFileInfo = $("chatFileInfo");
const chatFileChip = $("chatFileChip");
const chatFileName = $("chatFileName");
const attachMenuBtn = $("attachMenuBtn");
const attachMenu = $("attachMenu");
const attachFileAction = $("attachFileAction");

let chatAttachment = null;
const THEME_KEY = "asisvoz_theme";

if (window.pdfjsLib) {
  window.pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
}

function activateTab(tabName) {
  const isTx = tabName === "transcriptor";
  tabTranscriptor.classList.toggle("active", isTx);
  tabChatbot.classList.toggle("active", !isTx);
  panelTranscriptor.classList.toggle("active", isTx);
  panelChatbot.classList.toggle("active", !isTx);
}

tabTranscriptor.addEventListener("click", () => activateTab("transcriptor"));
tabChatbot.addEventListener("click", () => activateTab("chatbot"));

function getTxHistory() {
  const data = AsisVoz.getJson(AsisVoz.STORAGE_KEYS.history, []);
  return Array.isArray(data) ? data : [];
}

function setTxHistory(items) {
  AsisVoz.setJson(AsisVoz.STORAGE_KEYS.history, items.slice(0, 50));
}

function pushTxHistory(item) {
  const current = getTxHistory();
  current.unshift(item);
  setTxHistory(current);
}

function removeTxHistory(itemToDelete) {
  const current = getTxHistory();
  const next = current.filter((it) => !(it.fileName === itemToDelete.fileName && it.createdAt === itemToDelete.createdAt));
  setTxHistory(next);
}

async function createWordBlob(lines, sourceName) {
  if (!window.docx) throw new Error("No cargaron librerias para Word.");
  const { Document, Packer, Paragraph, HeadingLevel, AlignmentType } = window.docx;
  const now = new Date().toLocaleString("es-CO");
  const children = [
    new Paragraph({ text: "Transcripcion de audio", heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER }),
    new Paragraph({ text: `Archivo: ${sourceName}`, alignment: AlignmentType.CENTER }),
    new Paragraph({ text: `Fecha: ${now}`, alignment: AlignmentType.CENTER }),
    new Paragraph({ text: "" }),
    ...lines.map((line) => new Paragraph({ text: line })),
  ];
  const doc = new Document({ sections: [{ children }] });
  return Packer.toBlob(doc);
}

async function saveWordDocument(fileName, lines, sourceName) {
  const blob = await createWordBlob(lines, sourceName);
  const pickerSupported = typeof window.showSaveFilePicker === "function";

  if (pickerSupported) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: fileName,
        types: [{ description: "Word Document", accept: { "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"] } }],
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return;
    } catch (err) {
      if (err && err.name === "AbortError") return;
    }
  }

  window.saveAs(blob, fileName);
}

async function openPdfPreview(sourceName, lines) {
  if (!window.jspdf || !window.jspdf.jsPDF) {
    alert("No cargaron librerias para PDF.");
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const margin = 40;
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const maxWidth = pageWidth - margin * 2;
  let y = margin;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text("Transcripcion de audio", margin, y);
  y += 24;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.text(`Archivo: ${sourceName}`, margin, y);
  y += 14;
  doc.text(`Fecha: ${new Date().toLocaleString("es-CO")}`, margin, y);
  y += 20;

  doc.setFontSize(11);
  for (const line of lines) {
    const pieces = doc.splitTextToSize(line || " ", maxWidth);
    for (const piece of pieces) {
      if (y > pageHeight - margin) {
        doc.addPage();
        y = margin;
      }
      doc.text(piece, margin, y);
      y += 15;
    }
  }

  const blob = doc.output("blob");
  const blobUrl = URL.createObjectURL(blob);
  const opened = window.open(blobUrl, "_blank");
  setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
  if (!opened) {
    alert("El navegador bloqueo la nueva pestana. Permite pop-ups para este sitio.");
  }
}

async function readTextFile(file) {
  return file.text();
}

async function readDocxFile(file) {
  if (!window.mammoth) {
    throw new Error("No se pudo cargar el lector DOCX.");
  }
  const buffer = await file.arrayBuffer();
  const result = await window.mammoth.extractRawText({ arrayBuffer: buffer });
  return result.value || "";
}

async function readPdfFile(file) {
  if (!window.pdfjsLib) {
    throw new Error("No se pudo cargar el lector PDF.");
  }
  const bytes = new Uint8Array(await file.arrayBuffer());
  const pdf = await window.pdfjsLib.getDocument({ data: bytes }).promise;
  const maxPages = Math.min(pdf.numPages, 10);
  let output = "";
  for (let p = 1; p <= maxPages; p += 1) {
    const page = await pdf.getPage(p);
    const content = await page.getTextContent();
    const text = content.items.map((i) => i.str || "").join(" ");
    output += `\n[Pagina ${p}]\n${text}\n`;
  }
  return output;
}

function trimAttachmentText(text) {
  const normalized = String(text || "").replace(/\s+/g, " ").trim();
  return normalized.slice(0, 12000);
}

chatFileInput.addEventListener("change", async () => {
  const file = chatFileInput.files?.[0];
  if (!file) {
    chatAttachment = null;
    chatFileInfo.textContent = "";
    chatFileChip.classList.add("hidden");
    return;
  }

  chatFileInfo.textContent = `Procesando adjunto: ${file.name}...`;
  try {
    const ext = (file.name.split(".").pop() || "").toLowerCase();
    let text = "";
    if (ext === "txt") text = await readTextFile(file);
    else if (ext === "docx") text = await readDocxFile(file);
    else if (ext === "pdf") text = await readPdfFile(file);
    else throw new Error("Formato no soportado. Usa PDF, DOCX o TXT.");

    text = trimAttachmentText(text);
    if (!text) throw new Error("No se pudo extraer texto del archivo.");

    chatAttachment = {
      name: file.name,
      text,
    };
    chatFileName.textContent = file.name;
    chatFileChip.classList.remove("hidden");
    chatFileInfo.textContent = `Adjunto listo: ${file.name}`;
  } catch (err) {
    chatAttachment = null;
    chatFileInput.value = "";
    chatFileInfo.textContent = "";
    chatFileChip.classList.add("hidden");
    alert(err.message || "No se pudo procesar el adjunto.");
  }
});

function clearChatAttachmentSafe() {
  chatAttachment = null;
  chatFileInput.value = "";
  chatFileInfo.textContent = "";
  chatFileChip.classList.add("hidden");
}

function setChatAttachmentSafe(name, text) {
  const clean = trimAttachmentText(text);
  if (!clean) return;
  chatAttachment = { name, text: clean };
  chatFileName.textContent = name;
  chatFileChip.classList.remove("hidden");
  chatFileInfo.textContent = `Adjunto listo: ${name}`;
}

window.clearChatAttachmentSafe = clearChatAttachmentSafe;

clearChatFileBtn.addEventListener("click", (e) => {
  e.preventDefault();
  e.stopPropagation();
  clearChatAttachmentSafe();
});

// Ensure the chip never stays visible without a real attachment.
if (!chatAttachment || !chatFileName.textContent.trim()) {
  chatFileChip.classList.add("hidden");
}

attachMenuBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  attachMenu.classList.toggle("hidden");
});

attachFileAction.addEventListener("click", () => {
  attachMenu.classList.add("hidden");
  chatFileInput.click();
});

document.addEventListener("click", (e) => {
  if (!attachMenu.contains(e.target) && e.target !== attachMenuBtn) {
    attachMenu.classList.add("hidden");
  }
});

function renderTxHistory() {
  const items = getTxHistory();
  historyList.innerHTML = "";
  if (!items.length) {
    historyList.innerHTML = "<li>Sin historial.</li>";
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    const label = document.createElement("div");
    label.textContent = `${item.fileName} - ${new Date(item.createdAt).toLocaleString()}`;

    const wordBtn = document.createElement("button");
    wordBtn.className = "mini-btn";
    wordBtn.textContent = "Descargar Word";
    wordBtn.addEventListener("click", async () => {
      await saveWordDocument(item.fileName, item.lines, item.sourceName);
    });

    const pdfBtn = document.createElement("button");
    pdfBtn.className = "mini-btn";
    pdfBtn.textContent = "Ver PDF";
    pdfBtn.addEventListener("click", async () => {
      await openPdfPreview(item.sourceName, item.lines);
    });

    const askBtn = document.createElement("button");
    askBtn.className = "mini-btn";
    askBtn.textContent = "Preguntar al chatbot";
    askBtn.addEventListener("click", () => {
      setChatAttachmentSafe(item.fileName, (item.lines || []).join("\n"));
      activateTab("chatbot");
      if (!chatInput.value.trim()) {
        chatInput.value = "Analiza el archivo adjunto y dame un resumen con puntos clave.";
      }
      chatInput.focus();
      chatInput.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "mini-btn danger-btn";
    deleteBtn.textContent = "Eliminar";
    deleteBtn.addEventListener("click", () => {
      if (!confirm(`Eliminar "${item.fileName}" del historial?`)) return;
      removeTxHistory(item);
      renderTxHistory();
    });

    const actions = document.createElement("div");
    actions.className = "history-actions";
    actions.appendChild(wordBtn);
    actions.appendChild(pdfBtn);
    actions.appendChild(askBtn);
    actions.appendChild(deleteBtn);

    li.appendChild(label);
    li.appendChild(actions);
    historyList.appendChild(li);
  });
}

function showLoader(show) {
  transcribeLoader.classList.toggle("hidden", !show);
}

audioInput.addEventListener("change", () => {
  const file = audioInput.files?.[0];
  selectedFileName.textContent = file ? file.name : "Sin archivo cargado";
});

clearFileBtn.addEventListener("click", () => {
  audioInput.value = "";
  selectedFileName.textContent = "Sin archivo cargado";
});

transcribeBtn.addEventListener("click", async () => {
  const deepgramKey = AsisVoz.get(AsisVoz.STORAGE_KEYS.deepgramKey);
  const file = audioInput.files?.[0];
  if (!file) {
    AsisVoz.setStatus(transcribeStatus, "Selecciona un archivo primero.", false);
    return;
  }

  transcribeBtn.disabled = true;
  showLoader(true);
  AsisVoz.setStatus(transcribeStatus, "Transcribiendo...", true);

  try {
    const res = await AsisVoz.transcribeFile(file, deepgramKey);
    const lines = AsisVoz.buildTranscriptLines(res);
    const docxName = `${AsisVoz.sanitizeFilename(file.name)}.docx`;
    await saveWordDocument(docxName, lines, file.name);

    pushTxHistory({
      fileName: docxName,
      sourceName: file.name,
      createdAt: new Date().toISOString(),
      lines,
    });
    renderTxHistory();

    AsisVoz.setStatus(transcribeStatus, "", true);
    alert(`Listo: ${docxName}`);
  } catch (err) {
    AsisVoz.setStatus(transcribeStatus, "", false);
    alert(err.message || "No se pudo transcribir.");
  } finally {
    transcribeBtn.disabled = false;
    showLoader(false);
  }
});

async function loadBalance() {
  const key = AsisVoz.get(AsisVoz.STORAGE_KEYS.deepgramKey);
  if (!key) {
    balancePill.textContent = "Sin key de Deepgram";
    return;
  }
  const balance = await AsisVoz.deepgramBalance(key);
  if (String(balance).toLowerCase().includes("cors")) {
    balancePill.textContent = "Balance no disponible en navegador";
    return;
  }
  balancePill.textContent = balance;
}

function getChatHistory() {
  const data = AsisVoz.getJson(AsisVoz.STORAGE_KEYS.chatHistory, []);
  return Array.isArray(data) ? data : [];
}

function setChatHistory(items) {
  AsisVoz.setJson(AsisVoz.STORAGE_KEYS.chatHistory, items.slice(-30));
}

function renderChat() {
  const history = getChatHistory();
  chatBox.innerHTML = "";
  if (!history.length) {
    const welcome = document.createElement("div");
    welcome.className = "bubble bubble-assistant";
    welcome.textContent = "Hola, soy AsisVoz. Elige un modelo free y te ayudo.";
    chatBox.appendChild(welcome);
    return;
  }
  history.forEach((m) => {
    const bubble = document.createElement("div");
    bubble.className = `bubble ${m.role === "user" ? "bubble-user" : "bubble-assistant"}`;
    let content = String(m.content || "");
    // Hide raw attachment payloads from legacy/cached chat history entries.
    if (m.role === "user" && content.includes("[ADJUNTO:")) {
      const userLine = content.split("[ADJUNTO:")[0].trim();
      content = userLine || "Consulta sobre archivo adjunto";
    }
    bubble.textContent = content;
    chatBox.appendChild(bubble);
  });
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function loadFreeModels() {
  const openrouterKey = AsisVoz.get(AsisVoz.STORAGE_KEYS.openrouterKey);
  modelSelect.innerHTML = "<option value=''>Cargando modelos free...</option>";
  try {
    const models = await AsisVoz.fetchFreeOpenRouterModels(openrouterKey);
    if (!models.length) {
      modelSelect.innerHTML = "<option value=''>No hay modelos free disponibles</option>";
      return;
    }
    modelSelect.innerHTML = models
      .map((m) => `<option value="${m.id}">${m.name || m.id}</option>`)
      .join("");
  } catch (err) {
    modelSelect.innerHTML = "<option value=''>Error cargando modelos</option>";
    AsisVoz.setStatus(chatStatus, err.message || "No se pudieron cargar modelos free.", false);
  }
}

async function sendChat() {
  const text = chatInput.value.trim();
  if (!text && !chatAttachment) return;

  const openrouterKey = AsisVoz.get(AsisVoz.STORAGE_KEYS.openrouterKey);
  const model = modelSelect.value;
  if (!model) {
    AsisVoz.setStatus(chatStatus, "Selecciona un modelo free.", false);
    return;
  }

  const userContentParts = [];
  if (text) userContentParts.push(text);
  if (chatAttachment) {
    userContentParts.push(
      `[ADJUNTO: ${chatAttachment.name}]\n` +
      `Usa este contenido para responder la pregunta:\n${chatAttachment.text}`
    );
  }
  const userContent = userContentParts.join("\n\n");

  const displayUserText = text || "Consulta sobre archivo adjunto";
  const history = getChatHistory();
  history.push({ role: "user", content: displayUserText });
  setChatHistory(history);
  renderChat();
  chatInput.value = "";
  if (chatAttachment) {
    chatAttachment = null;
    chatFileInput.value = "";
    chatFileInfo.textContent = "";
    chatFileChip.classList.add("hidden");
  }

  sendBtn.disabled = true;
  AsisVoz.setStatus(chatStatus, `Consultando ${model}...`, true);
  try {
    const requestMessages = history.map((m, idx) => {
      if (idx === history.length - 1 && m.role === "user") {
        return { role: "user", content: userContent };
      }
      return m;
    });

    const response = await AsisVoz.chatCompletion(openrouterKey, model, requestMessages);
    const next = getChatHistory();
    next.push({ role: "assistant", content: response });
    setChatHistory(next);
    renderChat();
    AsisVoz.setStatus(chatStatus, `Respuesta recibida (${model}).`, true);
  } catch (err) {
    let msg = err.message || "Error consultando chatbot.";
    if (msg === "Failed to fetch" || /networkerror|no se pudo conectar/i.test(msg)) {
      msg = "No se pudo conectar con OpenRouter. Revisa internet, API key o bloqueadores del navegador.";
    }
    if (msg.includes("429")) {
      AsisVoz.setStatus(chatStatus, "OpenRouter 429: limite de uso/rate limit. Prueba otro modelo free o espera 1-2 minutos.", false);
      alert("OpenRouter 429: limite alcanzado. Cambia de modelo free o espera un momento.");
    } else {
      AsisVoz.setStatus(chatStatus, msg, false);
      alert(msg);
    }
  } finally {
    sendBtn.disabled = false;
  }
}

sendBtn.addEventListener("click", sendChat);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendChat();
  }
});

clearChatBtn.addEventListener("click", () => {
  setChatHistory([]);
  renderChat();
  clearChatAttachmentSafe();
});

reloadModelsBtn.addEventListener("click", loadFreeModels);

function applyTheme(theme) {
  const isDark = theme === "dark";
  document.body.classList.toggle("theme-dark", isDark);
  themeToggle.checked = isDark;
}

themeToggle.addEventListener("change", () => {
  const next = themeToggle.checked ? "dark" : "light";
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
});

activateTab("transcriptor");
renderTxHistory();
renderChat();
loadBalance().catch(() => {
  balancePill.textContent = "Saldo no disponible";
});
loadFreeModels();
applyTheme(localStorage.getItem(THEME_KEY) || "light");
