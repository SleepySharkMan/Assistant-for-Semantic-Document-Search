export const messageHistoryKey = "chatMessages";

/**
 * Добавляет сообщение в DOM и сохраняет его в localStorage.
 * @param {string} text - Текст сообщения
 * @param {string} sender - "user" или "bot"
 */
export function addMessage(text, sender) {
  const messagesContainer = document.getElementById("messages");

  const msg = document.createElement("div");
  msg.className = `message ${sender}-message`;

  const safeText = document.createElement("p");
  safeText.textContent = text;

  const content = document.createElement("div");
  content.className = "message-content";
  content.appendChild(safeText);

  msg.appendChild(content);

  if (sender === "bot") {
    // Кнопка воспроизведения/остановки речи
    const playBtn = document.createElement("button");
    playBtn.className = "play-audio-btn";
    playBtn.setAttribute("aria-label", "Озвучить");

    const playIcon = document.createElement("i");
    playIcon.classList.add("audio-icon");
    playBtn.appendChild(playIcon);

    msg.appendChild(playBtn);
  }

  messagesContainer.appendChild(msg);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  const stored = getStoredMessages();
  stored.push({ text, sender });
  localStorage.setItem(messageHistoryKey, JSON.stringify(stored));
}

/**
 * Удаляет все сообщения из DOM и localStorage.
 */
export function clearMessages() {
  const messagesContainer = document.getElementById("messages");
  messagesContainer.innerHTML = "";
  localStorage.removeItem(messageHistoryKey);
}

/**
 * Возвращает список сообщений из localStorage.
 */
export function getStoredMessages() {
  return JSON.parse(localStorage.getItem(messageHistoryKey)) || [];
}

/**
 * Загружает сообщения с сервера и отображает их в DOM.
 * @param {string} user_id
 */
export async function loadServerMessages(user_id) {
  try {
    const response = await fetch(`/api/history?user_id=${encodeURIComponent(user_id)}`);
    if (!response.ok) throw new Error("Ошибка получения истории");

    const data = await response.json();
    if (Array.isArray(data.messages)) {
      data.messages.forEach(msg => addMessage(msg.text, msg.sender));
    }
  } catch (error) {
    console.error("❌ Ошибка загрузки истории:", error);
  }
}
