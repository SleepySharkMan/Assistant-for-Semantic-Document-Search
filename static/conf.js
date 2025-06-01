const SPLITTER_METHOD = {
  "words": "по словам",
  "sentences": "по предложениям",
  "paragraphs": "по параграфам",
  "unknown": "неизвестно"
};

// Подключение к Socket.IO для получения логов
let socket;
function initWebSocket() {
  socket = io("/ws/logs", { transports: ["websocket"] });

  socket.on("connect", () => {
    console.log("Socket.IO подключено для получения логов");
    appendLog({ timestamp: new Date().toISOString(), level: "INFO", message: "Socket.IO подключён" });
  });

  socket.on("log_message", (data) => {
    appendLog(data);
  });

  socket.on("disconnect", () => {
    console.log("Socket.IO отключено, попытка переподключения...");
    appendLog({ timestamp: new Date().toISOString(), level: "ERROR", message: "Socket.IO отключено" });
  });

  socket.on("connect_error", (error) => {
    console.error("Ошибка подключения Socket.IO:", error);
    appendLog({ timestamp: new Date().toISOString(), level: "ERROR", message: `Ошибка подключения: ${error.message}` });
  });
}

// Добавление лога в интерфейс
function appendLog(log) {
  const logsContainer = document.getElementById("logs-container");
  if (!logsContainer) return;
  const logElement = document.createElement("div");
  logElement.className = `log-entry log-${log.level.toLowerCase()}`;
  logElement.textContent = `${log.timestamp} ${log.level}: ${log.message}`;
  logsContainer.appendChild(logElement);
  while (logsContainer.childElementCount > 100) {
    logsContainer.removeChild(logsContainer.firstChild);
  }
  logsContainer.scrollTop = logsContainer.scrollHeight;
}

// Уведомления
function showToast(message, type = "info") {
  let container = document.getElementById("container");
  if (!container) {
    container = document.createElement("div");
    container.id = "container";
    container.style.position = "fixed";
    container.style.top = "20px";
    container.style.right = "20px";
    container.style.zIndex = "9999";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  toast.style.marginTop = "10px";
  toast.style.padding = "10px 15px";
  toast.style.borderRadius = "4px";
  toast.style.color = "#fff";
  toast.style.minWidth = "200px";
  if (type === "success") {
    toast.style.backgroundColor = "#28a745";
  } else if (type === "error") {
    toast.style.backgroundColor = "#dc3545";
  } else if (type === "warning") {
    toast.style.backgroundColor = "#ffc107";
  } else {
    toast.style.backgroundColor = "#007bff";
  }

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => {
      if (container.contains(toast)) {
        container.removeChild(toast);
      }
      if (container.childElementCount === 0) {
        document.body.removeChild(container);
      }
    }, 300);
  }, 3000);
}

// Утилиты для работы с объектом по "точечному" пути
function getValueByPath(obj, path) {
  const keys = path.split(".");
  let current = obj;
  for (const key of keys) {
    if (current == null || typeof current !== "object" || !(key in current)) {
      return undefined;
    }
    current = current[key];
  }
  return current;
}

function setValueByPath(obj, path, value) {
  const keys = path.split(".");
  let current = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    if (!(key in current) || typeof current[key] !== "object" || current[key] === null) {
      current[key] = {};
    }
    current = current[key];
  }
  current[keys[keys.length - 1]] = value;
}

// Сбор данных из формы
function collectForm() {
  const cfg = {};
  document.querySelectorAll(".config-form [name]").forEach(el => {
    const fullName = el.name.trim();
    let value;
    if (el.type === "checkbox") {
      value = el.checked;
    } else {
      value = el.value;
    }
    if (el.type === "number") {
      const num = Number(value);
      if (!isNaN(num)) {
        value = num;
      }
    }
    const keys = fullName.split(".");
    if (keys.length === 1) {
      cfg[keys[0]] = value;
    } else {
      setValueByPath(cfg, fullName, value);
    }
  });
  return cfg;
}

// Заполнение формы из конфигурации
function fillForm(cfg, parentKey = "") {
  Object.keys(cfg).forEach(key => {
    const fullKey = parentKey ? `${parentKey}.${key}` : key;
    const value = cfg[key];
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      fillForm(value, fullKey);
    } else {
      const input = document.querySelector(`.config-form [name="${fullKey}"]`);
      if (input) {
        if (input.type === "checkbox") {
          input.checked = Boolean(value);
        } else if (input.tagName.toLowerCase() === "textarea") {
          input.value = value;
        } else {
          input.value = value;
        }
      }
    }
  });
}

// Загрузка конфигурации с сервера
async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    if (data.status === "success") {
      const cfg = data.config;
      fillForm(cfg);
      showToast("Конфигурация загружена", "success");
    } else {
      const msg = data.message || "Не удалось загрузить конфигурацию";
      showToast(msg, "error");
    }
  } catch (err) {
    console.error("Ошибка при loadConfig:", err);
    showToast("Ошибка сети при загрузке конфигурации", "error");
  }
}

// Сохранение конфигурации на сервер
async function saveConfig() {
  const cfg = collectForm();
  try {
    const response = await fetch("/api/config", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(cfg)
    });
    const data = await response.json();
    if (response.ok && data.status === "success") {
      showToast("Конфигурация сохранена", "success");
    } else {
      const msg = data.message || "Не удалось сохранить конфигурацию";
      showToast(msg, "error");
    }
  } catch (err) {
    console.error("Ошибка при saveConfig:", err);
    showToast("Ошибка сети при сохранении конфигурации", "error");
  }
}

// Подбор/оптимизация параметров
async function optimizeConfig() {
  try {
    const response = await fetch("/api/config/optimize");
    const data = await response.json();
    if (response.ok && data.status === "success") {
      showToast("Параметры успешно подобраны", "success");
      await loadConfig();
    } else {
      const msg = data.message || "Ошибка при подборе параметров";
      showToast(msg, "error");
    }
  } catch (err) {
    console.error("Ошибка при optimizeConfig:", err);
    showToast("Ошибка сети при подборе параметров", "error");
  }
}

// Обновление списка файлов
async function loadFiles() {
  showToast("Запрос списка файлов...", "info");
  try {
    const response = await fetch("/api/files");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    if (data.status === "success" && Array.isArray(data.files)) {
      const tbody = document.querySelector(".documents-section .documents-list tbody");
      if (!tbody) {
        showToast("Ошибка: таблица документов не найдена", "error");
        return;
      }
      tbody.innerHTML = "";
      data.files.forEach(file => {
        if (!file || !file.name) {
          console.warn("Пропущен некорректный файл:", file);
          return;
        }
        const tr = document.createElement("tr");
        const tdName = document.createElement("td");
        tdName.textContent = file.name || "Неизвестное имя файла";
        tr.appendChild(tdName);
        const tdSize = document.createElement("td");
        tdSize.textContent = file.size || "-";
        tr.appendChild(tdSize);
        const tdModified = document.createElement("td");
        tdModified.textContent = file.modified || "-";
        tr.appendChild(tdModified);
        const tdSplitter = document.createElement("td");
        tdSplitter.textContent = SPLITTER_METHOD[file.splitter_method] || "неизвестно";
        tr.appendChild(tdSplitter);
        const tdActions = document.createElement("td");
        const divActions = document.createElement("div");
        divActions.className = "document-actions";
        const btnDelete = document.createElement("button");
        btnDelete.className = "document-action delete-action";
        btnDelete.dataset.filename = file.name;
        btnDelete.textContent = "Удалить";
        btnDelete.addEventListener("click", () => deleteFile(file.name));
        divActions.appendChild(btnDelete);
        const btnRecreate = document.createElement("button");
        btnRecreate.className = "document-action recreate-action";
        btnRecreate.dataset.filename = file.name;
        btnRecreate.textContent = "Пересоздать эмбеддинги";
        btnRecreate.addEventListener("click", () => rebuildFileEmbeddings(file.name));
        divActions.appendChild(btnRecreate);
        tdActions.appendChild(divActions);
        tr.appendChild(tdActions);
        tbody.appendChild(tr);
      });
      showToast("Список файлов обновлен", "success");
    } else {
      showToast("Список файлов пуст или не получен", "info");
    }
  } catch (err) {
    console.error("Ошибка при loadFiles:", err);
    showToast("Ошибка сети при обновлении списка файлов", "error");
  }
}

// Удаление файла
async function deleteFile(filename) {
  if (!confirm(`Вы действительно хотите удалить файл "${filename}"?`)) {
    return;
  }
  try {
    const response = await fetch(`/api/files/${encodeURIComponent(filename)}`, {
      method: "DELETE"
    });
    const data = await response.json();
    if (response.ok && data.status === "success") {
      showToast(`Файл "${filename}" удалён`, "success");
      await loadFiles();
    } else {
      const msg = data.message || "Не удалось удалить файл";
      showToast(`Ошибка: ${msg}`, "error");
    }
  } catch (err) {
    console.error("Ошибка при deleteFile:", err);
    showToast("Ошибка сети при удалении файла", "error");
  }
}

// Пересоздание эмбеддингов для файла
async function rebuildFileEmbeddings(filename) {
  if (!confirm(`Пересоздать эмбеддинги для "${filename}"?`)) {
    return;
  }
  try {
    const response = await fetch(`/api/files/${encodeURIComponent(filename)}/rebuild`, {
      method: "POST"
    });
    const data = await response.json();
    if (response.ok && data.status === "success") {
      showToast(`Эмбеддинги для "${filename}" пересозданы`, "success");
      await loadFiles();
    } else {
      const msg = data.message || "Не удалось пересоздать эмбеддинги";
      showToast(`Ошибка: ${msg}`, "error");
    }
  } catch (err) {
    console.error("Ошибка при rebuildFileEmbeddings:", err);
    showToast("Ошибка сети при пересоздании эмбеддингов", "error");
  }
}

// Запуск приложения
async function startApp() {
  if (!confirm("Вы уверены, что хотите запустить сервис?")) {
    return;
  }
  const startBtn = document.getElementById("start-app");
  if (startBtn) {
    startBtn.disabled = true;
  }
  try {
    const response = await fetch("/api/app/start", { method: "POST" });
    const data = await response.json();
    if (response.ok && data.status === "success") {
      showToast("Сервис запущен", "success");
      await new Promise(resolve => setTimeout(resolve, 500));
      await updateStatus();
      window.open("http://localhost:8000", "_blank");
    } else {
      const msg = data.message || "Не удалось запустить сервис";
      showToast(msg, "error");
      if (startBtn) {
        startBtn.disabled = false;
      }
    }
  } catch (err) {
    console.error("Ошибка при startApp:", err);
    showToast("Ошибка сети при запуске сервиса", "error");
    if (startBtn) {
      startBtn.disabled = false;
    }
  }
}

async function stopApp() {
  if (!confirm("Вы уверены, что хотите остановить сервис?")) {
    return;
  }
  const stopBtn = document.getElementById("stop-app");
  if (stopBtn) {
    stopBtn.disabled = true;
  }
  try {
    const response = await fetch("/api/app/stop", { method: "POST" });
    const data = await response.json();
    if (response.ok && data.status === "success") {
      showToast("Сервис остановлен", "success");
      await updateStatus();
    } else {
      const msg = data.message || "Не удалось остановить сервис";
      showToast(msg, "error");
      if (stopBtn) {
        stopBtn.disabled = false;
      }
    }
  } catch (err) {
    console.error("Ошибка при stopApp:", err);
    showToast("Ошибка сети при остановке сервиса", "error");
    if (stopBtn) {
      stopBtn.disabled = false;
    }
  }
}

async function shutdownApp() {
  if (!confirm("Вы уверены, что хотите закрыть приложение?")) {
    return;
  }
  try {
    const response = await fetch("/api/app/shutdown", { method: "POST" });
    const data = await response.json();
    if (response.ok && data.status === "success") {
      showToast("Приложение закрыто", "success");
      await updateStatus();
    } else {
      const msg = data.message || "Не удалось закрыть приложение";
      showToast(msg, "error");
    }
  } catch (err) {
    console.error("Ошибка при shutdownApp:", err);
    showToast("Ошибка сети при закрытии приложения", "error");
  }
}

async function updateStatus() {
  try {
    const response = await fetch("/api/app/status");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    console.log("Статус от сервера:", data);
    const statusEl = document.getElementById("service-status");
    const startBtn = document.getElementById("start-app");
    const stopBtn = document.getElementById("stop-app");
    if (statusEl) {
      statusEl.textContent = data.running ? "Запущено" : "Остановлено";
      statusEl.style.color = data.running ? "green" : "red";
    }
    if (startBtn) {
      startBtn.disabled = data.running;
    }
    if (stopBtn) {
      stopBtn.disabled = !data.running;
    }
  } catch (err) {
    console.error("Ошибка при updateStatus:", err);
    const statusEl = document.getElementById("service-status");
    if (statusEl) {
      statusEl.textContent = "ошибка";
      statusEl.style.color = "red";
    }
  }
}

async function addFile() {
  const fileInput = document.getElementById("file-input");
  if (!fileInput) {
    showToast("Ошибка: элемент file-input не найден", "error");
    return;
  }
  fileInput.click();
}

function handleFileSelect() {
  const fileInput = document.getElementById("file-input");
  const addBtn = document.getElementById("add-file");
  return async function() {
    if (!fileInput || !addBtn) {
      showToast("Ошибка: элементы формы не найдены", "error");
      return;
    }
    const files = fileInput.files;
    if (files.length === 0) {
      showToast("Файлы не выбраны", "error");
      return;
    }
    addBtn.disabled = true;
    addBtn.textContent = "Загрузка...";
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }
    if (!confirm("Перезаписать существующие файлы, если они есть?")) {
      addBtn.disabled = false;
      addBtn.textContent = "Добавить файл";
      fileInput.value = "";
      showToast("Загрузка отменена", "info");
      return;
    }
    formData.append("overwrite", "true");
    try {
      const response = await fetch("/api/files/upload", {
        method: "POST",
        body: formData
      });
      const data = await response.json();
      if (response.ok && (data.status === "success" || data.status === "partial_success")) {
        let message = data.message || "Файлы загружены";
        if (data.errors && data.errors.length > 0) {
          message += `. Ошибки: ${data.errors.map(e => `${e.filename}: ${e.error}`).join(", ")}`;
        }
        showToast(message, data.status === "success" ? "success" : "warning");
        await loadFiles();
      } else {
        const msg = data.message || "Не удалось загрузить файлы";
        showToast(`Ошибка: ${msg}`, "error");
      }
    } catch (err) {
      console.error("Ошибка при добавлении файлов:", err);
      showToast("Ошибка сети при добавлении файлов", "error");
    } finally {
      addBtn.disabled = false;
      addBtn.textContent = "Добавить файл";
      fileInput.value = "";
    }
  };
}

async function rebuildAllEmbeddings() {
  if (!confirm("Пересоздать эмбеддинги для всех файлов? Это может занять время")) {
    return;
  }
  const rebuildBtn = document.getElementById("rebuild-all-embeddings");
  if (rebuildBtn) {
    rebuildBtn.disabled = true;
    rebuildBtn.textContent = "Пересчет...";
  }
  try {
    const response = await fetch("/api/files/rebuild-all", {
      method: "POST"
    });
    const data = await response.json();
    if (response.ok && data.status === "success") {
      showToast(data.message || "Эмбеддинги пересозданы", "success");
      await loadFiles();
    } else {
      const msg = data.message || "Не удалось пересоздать эмбеддинги";
      showToast(`Ошибка: ${msg}`, "error");
    }
  } catch (err) {
    console.error("Ошибка при rebuildAllEmbeddings:", err);
    showToast("Ошибка сети при пересоздании эмбеддингов", "error");
  } finally {
    if (rebuildBtn) {
      rebuildBtn.disabled = false;
      rebuildBtn.textContent = "Пересчитать эмбеддинги";
    }
  }
}

function setupFieldsetCollapse() {
  document.querySelectorAll(".config-form fieldset").forEach(fieldset => {
    const legend = fieldset.querySelector("legend");
    if (!legend) return;
    legend.style.cursor = "pointer";
    legend.addEventListener("click", () => {
      fieldset.classList.toggle("collapsed");
    });
  });
}

function setupSectionCollapse() {
  document.querySelectorAll("section .toggle-section").forEach(toggle => {
    const title = toggle.textContent.trim();
    toggle.style.cursor = "pointer";
    toggle.addEventListener("click", () => {
      const section = toggle.closest("section");
      if (!section) return;
      const isCollapsed = section.classList.toggle("collapsed");
      toggle.textContent = isCollapsed ? `Показать ${title}` : title;
    });
  });

  document.querySelectorAll(".logs-section > .logs-section > h2").forEach(h2 => {
    const title = h2.textContent.trim();
    h2.style.cursor = "pointer";
    h2.addEventListener("click", () => {
      const innerLogsSection = h2.closest(".logs-section");
      if (!innerLogsSection) return;
      const logsContainer = innerLogsSection.querySelector("#logs-container");
      if (!logsContainer) return;
      const isCollapsed = innerLogsSection.classList.toggle("collapsed");
      if (isCollapsed) {
        logsContainer.style.display = "none";
        h2.textContent = `Показать ${title}`;
      } else {
        logsContainer.style.display = "";
        h2.textContent = title;
      }
    });
  });
}

function init() {
  const saveBtn = document.getElementById("apply-changes");
  if (saveBtn) {
    saveBtn.addEventListener("click", saveConfig);
  }

  const reloadBtn = document.getElementById("reload-btn");
  if (reloadBtn) {
    reloadBtn.addEventListener("click", loadConfig);
  }

  const optimizeBtn = document.getElementById("optimize-params");
  if (optimizeBtn) {
    optimizeBtn.addEventListener("click", optimizeConfig);
  }

  const refreshBtn = document.getElementById("refresh-files");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", loadFiles);
  }

  const startBtn = document.getElementById("start-app");
  if (startBtn) {
    startBtn.addEventListener("click", startApp);
  }

  const stopBtn = document.getElementById("stop-app");
  if (stopBtn) {
    stopBtn.addEventListener("click", stopApp);
  }

  const shutdownBtn = document.getElementById("shutdown-app");
  if (shutdownBtn) {
    shutdownBtn.addEventListener("click", shutdownApp);
  }

  const addFileBtn = document.getElementById("add-file");
  if (addFileBtn) {
    addFileBtn.addEventListener("click", addFile);
  }

  const fileInput = document.getElementById("file-input");
  if (fileInput) {
    fileInput.addEventListener("change", handleFileSelect());
  }

  const rebuildAllBtn = document.getElementById("rebuild-all-embeddings");
  if (rebuildAllBtn) {
    rebuildAllBtn.addEventListener("click", rebuildAllEmbeddings);
  }
  setupFieldsetCollapse();
  setupSectionCollapse();
  initWebSocket(); 
}

// Запуск после загрузки страницы
window.addEventListener("DOMContentLoaded", () => {
  loadConfig();
  loadFiles();
  updateStatus();
  init();
});