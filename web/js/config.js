const $ = (id) => document.getElementById(id);

const licenseInput = $("licenseInput");
const deepgramInput = $("deepgramInput");
const openrouterInput = $("openrouterInput");

const saveLicenseBtn = $("saveLicenseBtn");
const saveDeepgramBtn = $("saveDeepgramBtn");
const saveOpenrouterBtn = $("saveOpenrouterBtn");
const goDashboardBtn = $("goDashboardBtn");

const licenseStatus = $("licenseStatus");
const deepgramStatus = $("deepgramStatus");
const openrouterStatus = $("openrouterStatus");

function refreshStatus() {
  const hasLicense = AsisVoz.hasValidLicense();
  const hasDeepgram = Boolean(AsisVoz.get(AsisVoz.STORAGE_KEYS.deepgramKey));
  const hasOpenrouter = Boolean(AsisVoz.get(AsisVoz.STORAGE_KEYS.openrouterKey));

  AsisVoz.setStatus(licenseStatus, hasLicense ? "Licencia registrada" : "Licencia pendiente", hasLicense);
  AsisVoz.setStatus(deepgramStatus, hasDeepgram ? "Deepgram key lista" : "Deepgram key pendiente", hasDeepgram);
  AsisVoz.setStatus(openrouterStatus, hasOpenrouter ? "OpenRouter key lista" : "OpenRouter key pendiente", hasOpenrouter);

  if (AsisVoz.isReady()) {
    goDashboardBtn.classList.remove("disabled-link");
  } else {
    goDashboardBtn.classList.add("disabled-link");
  }
}

saveLicenseBtn.addEventListener("click", () => {
  const key = licenseInput.value.trim();
  if (!key) {
    AsisVoz.setStatus(licenseStatus, "Ingresa una licencia.", false);
    return;
  }
  if (!AsisVoz.LICENSES.has(key)) {
    AsisVoz.put(AsisVoz.STORAGE_KEYS.licenseValid, "false");
    AsisVoz.setStatus(licenseStatus, "Licencia invalida.", false);
    refreshStatus();
    return;
  }
  AsisVoz.put(AsisVoz.STORAGE_KEYS.licenseValid, "true");
  AsisVoz.setStatus(licenseStatus, "Licencia validada.", true);
  refreshStatus();
});

saveDeepgramBtn.addEventListener("click", async () => {
  const key = deepgramInput.value.trim();
  if (!key) {
    AsisVoz.setStatus(deepgramStatus, "Ingresa Deepgram key.", false);
    return;
  }
  saveDeepgramBtn.disabled = true;
  AsisVoz.setStatus(deepgramStatus, "Validando...", true);
  try {
    const ok = await AsisVoz.validateDeepgramKey(key);
    if (!ok) throw new Error("No se pudo validar.");
    AsisVoz.put(AsisVoz.STORAGE_KEYS.deepgramKey, key);
    deepgramInput.value = "";
    AsisVoz.setStatus(deepgramStatus, "Deepgram key guardada.", true);
  } catch (err) {
    AsisVoz.setStatus(deepgramStatus, err.message || "Error al validar.", false);
  } finally {
    saveDeepgramBtn.disabled = false;
    refreshStatus();
  }
});

saveOpenrouterBtn.addEventListener("click", async () => {
  const key = openrouterInput.value.trim();
  if (!key) {
    AsisVoz.setStatus(openrouterStatus, "Ingresa OpenRouter key.", false);
    return;
  }
  saveOpenrouterBtn.disabled = true;
  AsisVoz.setStatus(openrouterStatus, "Validando...", true);
  try {
    const ok = await AsisVoz.validateOpenRouterKey(key);
    if (!ok) throw new Error("OpenRouter key invalida.");
    AsisVoz.put(AsisVoz.STORAGE_KEYS.openrouterKey, key);
    openrouterInput.value = "";
    AsisVoz.setStatus(openrouterStatus, "OpenRouter key guardada.", true);
  } catch (err) {
    AsisVoz.setStatus(openrouterStatus, err.message || "Error al validar.", false);
  } finally {
    saveOpenrouterBtn.disabled = false;
    refreshStatus();
  }
});

goDashboardBtn.addEventListener("click", (e) => {
  if (!AsisVoz.isReady()) {
    e.preventDefault();
    alert("Primero completa licencia + Deepgram + OpenRouter.");
  }
});

refreshStatus();
