(function () {
  const LICENSES = new Set([
    "A7X4D9-KLM3Q2-Z8N6YP",
    "P3W9XK-8JDLQ1-R2M4VT",
    "QZ8C1B-MN4V7E-5TPR6X",
  ]);

  const STORAGE_KEYS = {
    licenseValid: "asisvoz_license_valid",
    deepgramKey: "asisvoz_deepgram_key",
    openrouterKey: "asisvoz_openrouter_key",
    history: "asisvoz_history",
    chatHistory: "asisvoz_chat_history",
  };

  function setStatus(node, text, ok) {
    if (!node) return;
    node.textContent = text;
    node.classList.remove("ok", "error");
    node.classList.add(ok ? "ok" : "error");
  }

  function sanitizeFilename(name) {
    const raw = (name || "transcripcion")
      .replace(/\.[^.]+$/, "")
      .replace(/[^a-zA-Z0-9._-]/g, "_");
    return raw || "transcripcion";
  }

  function secToHHMMSS(seconds) {
    const s = Math.max(0, Math.floor(Number(seconds) || 0));
    const h = String(Math.floor(s / 3600)).padStart(2, "0");
    const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
    const r = String(s % 60).padStart(2, "0");
    return `${h}:${m}:${r}`;
  }

  function chooseBlockSize(durationSec) {
    if (durationSec <= 20 * 60) return 5 * 60;
    if (durationSec <= 60 * 60) return 15 * 60;
    return 30 * 60;
  }

  function get(key) {
    return (localStorage.getItem(key) || "").trim();
  }

  function put(key, value) {
    localStorage.setItem(key, value);
  }

  function remove(key) {
    localStorage.removeItem(key);
  }

  function hasValidLicense() {
    return get(STORAGE_KEYS.licenseValid) === "true";
  }

  function isReady() {
    return hasValidLicense() && Boolean(get(STORAGE_KEYS.deepgramKey)) && Boolean(get(STORAGE_KEYS.openrouterKey));
  }

  function clearAllConfig() {
    remove(STORAGE_KEYS.licenseValid);
    remove(STORAGE_KEYS.deepgramKey);
    remove(STORAGE_KEYS.openrouterKey);
    remove(STORAGE_KEYS.history);
    remove(STORAGE_KEYS.chatHistory);
  }

  function getJson(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return fallback;
      return JSON.parse(raw);
    } catch {
      return fallback;
    }
  }

  function setJson(key, data) {
    localStorage.setItem(key, JSON.stringify(data));
  }

  async function deepgramRequest(path, apiKey, options) {
    const url = `https://api.deepgram.com${path}`;
    const headers = Object.assign({}, options?.headers || {}, {
      Authorization: `Token ${apiKey}`,
    });
    const res = await fetch(url, Object.assign({}, options || {}, { headers }));
    if (!res.ok) {
      let details = "";
      try {
        const j = await res.json();
        details = j.err_msg || j.error || JSON.stringify(j);
      } catch {
        details = await res.text();
      }
      throw new Error(`Deepgram ${res.status}: ${details || "error"}`);
    }
    return res.json();
  }

  async function validateDeepgramKey(apiKey) {
    const data = await deepgramRequest("/v1/listen?model=nova-3&smart_format=true", apiKey, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: "https://dpgr.am/spacewalk.wav",
      }),
    });
    const alt = data?.results?.channels?.[0]?.alternatives?.[0];
    return Boolean((alt?.transcript || "").trim());
  }

  async function deepgramBalance(apiKey) {
    void apiKey;
    return "Balance no disponible en frontend (CORS en /projects)";
  }

  async function transcribeFile(file, apiKey) {
    const params = new URLSearchParams({
      model: "nova-2",
      language: "es",
      smart_format: "true",
      punctuate: "true",
      paragraphs: "true",
      diarize: "true",
    });
    return deepgramRequest(`/v1/listen?${params.toString()}`, apiKey, {
      method: "POST",
      headers: { "Content-Type": file.type || "application/octet-stream" },
      body: file,
    });
  }

  function buildTranscriptLines(response) {
    const duration = Number(response?.metadata?.duration || 0);
    const blockSize = chooseBlockSize(duration);
    const alternatives = response?.results?.channels?.[0]?.alternatives || [];
    const lines = [];
    let currentBlock = -1;

    for (const alt of alternatives) {
      const paragraphs = alt?.paragraphs?.paragraphs;
      if (Array.isArray(paragraphs) && paragraphs.length) {
        for (const p of paragraphs) {
          const start = Number(p.start || 0);
          const blockIndex = Math.floor(start / blockSize);
          if (blockIndex !== currentBlock) {
            currentBlock = blockIndex;
            const from = secToHHMMSS(blockIndex * blockSize);
            const to = secToHHMMSS(Math.min((blockIndex + 1) * blockSize, duration));
            lines.push(`==== Bloque ${from} - ${to} ====`);
            lines.push("");
          }
          const speakerId = p.speaker === undefined || p.speaker === null ? "?" : p.speaker;
          const text = (p.sentences || []).map((s) => s.text || "").join(" ").trim();
          if (text) lines.push(`Locutor ${speakerId}: ${text}`);
        }
        continue;
      }
      const transcript = (alt?.transcript || "").trim();
      if (transcript) lines.push(transcript);
    }

    if (!lines.length) throw new Error("No se detecto voz en el archivo.");
    return lines;
  }

  async function generateDocx(fileName, lines, sourceName) {
    if (!window.docx || !window.saveAs) {
      throw new Error("No cargaron librerias para exportar Word.");
    }
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
    const blob = await Packer.toBlob(doc);
    window.saveAs(blob, fileName);
  }

  async function openrouterRequest(path, apiKey, body) {
    const headers = {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "X-Title": "AsisVoz Frontend",
    };
    let res;
    try {
      res = await fetch(`https://openrouter.ai${path}`, {
        method: "POST",
        headers,
        body: JSON.stringify(body || {}),
      });
    } catch {
      // Retry once for transient network failures.
      try {
        res = await fetch(`https://openrouter.ai${path}`, {
          method: "POST",
          headers,
          body: JSON.stringify(body || {}),
        });
      } catch {
        throw new Error("No se pudo conectar con OpenRouter (red/CORS/popup blocker).");
      }
    }
    if (!res.ok) {
      let details = "";
      try {
        const j = await res.json();
        details = j.error?.message || JSON.stringify(j);
      } catch {
        details = await res.text();
      }
      throw new Error(`OpenRouter ${res.status}: ${details || "error"}`);
    }
    return res.json();
  }

  function isZeroPrice(value) {
    return String(value ?? "") === "0";
  }

  function isFreeOpenRouterModel(model) {
    const p = model?.pricing || {};
    const freeByPricing =
      isZeroPrice(p.prompt) &&
      isZeroPrice(p.completion) &&
      isZeroPrice(p.request) &&
      isZeroPrice(p.image) &&
      isZeroPrice(p.web_search) &&
      isZeroPrice(p.internal_reasoning) &&
      isZeroPrice(p.input_cache_read) &&
      isZeroPrice(p.input_cache_write);

    const id = String(model?.id || "");
    const freeById = id.endsWith(":free") || id === "openrouter/free";
    return freeByPricing || freeById;
  }

  async function fetchFreeOpenRouterModels(apiKey) {
    const res = await fetch("https://openrouter.ai/api/v1/models?output_modalities=text", {
      method: "GET",
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    if (!res.ok) {
      let details = "";
      try {
        const j = await res.json();
        details = j.error?.message || JSON.stringify(j);
      } catch {
        details = await res.text();
      }
      throw new Error(`OpenRouter ${res.status}: ${details || "error cargando modelos"}`);
    }

    const data = await res.json();
    const models = Array.isArray(data?.data) ? data.data : [];
    return models
      .filter(isFreeOpenRouterModel)
      .sort((a, b) => (a.name || a.id).localeCompare(b.name || b.id));
  }

  async function validateOpenRouterKey(apiKey) {
    const res = await fetch("https://openrouter.ai/api/v1/key", {
      method: "GET",
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    if (!res.ok) return false;
    return true;
  }

  async function chatCompletion(apiKey, model, messages) {
    if (!model) throw new Error("Selecciona un modelo para continuar.");
    const payload = {
      model,
      messages,
      temperature: 0.4,
    };
    const data = await openrouterRequest("/api/v1/chat/completions", apiKey, payload);
    const text = data?.choices?.[0]?.message?.content || "";
    if (!text) throw new Error("Respuesta vacia del modelo.");
    return text;
  }

  window.AsisVoz = {
    LICENSES,
    STORAGE_KEYS,
    setStatus,
    sanitizeFilename,
    get,
    put,
    remove,
    getJson,
    setJson,
    hasValidLicense,
    isReady,
    clearAllConfig,
    validateDeepgramKey,
    validateOpenRouterKey,
    deepgramBalance,
    transcribeFile,
    buildTranscriptLines,
    generateDocx,
    fetchFreeOpenRouterModels,
    chatCompletion,
  };
})();
