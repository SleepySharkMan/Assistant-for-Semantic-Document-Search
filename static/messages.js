export const messageHistoryKey = "chatMessages";

/**
 * Добавляет сообщение в DOM и сохраняет его в localStorage.
 * @param {string} text - Текст сообщения
 * @param {string} sender - "user" или "bot"
 */
export function addMessage(text, sender, sources = null, fragments = null) {
  const messagesContainer = document.getElementById("messages");

  const msg = document.createElement("div");
  msg.className = `message ${sender}-message`;

  const content = document.createElement("div");
  content.className = "message-content";

  const safeText = document.createElement("p");
  safeText.textContent = text;
  content.appendChild(safeText);

  // Добавляем источники и фрагменты, если они есть
  if (sender === "bot" && (sources || fragments)) {
      const details = document.createElement("div");
      details.className = "message-details";

      if (sources) {
          const sourcesDiv = document.createElement("div");
          sourcesDiv.className = "message-sources";
          const sourcesTitle = document.createElement("strong");
          sourcesTitle.textContent = "Источники:";
          sourcesDiv.appendChild(sourcesTitle);
          const sourcesList = document.createElement("ul");
          (Array.isArray(sources) ? sources : [sources]).forEach(src => {
              const li = document.createElement("li");
              li.textContent = src || "Неизвестный источник";
              sourcesList.appendChild(li);
          });
          sourcesDiv.appendChild(sourcesList);
          details.appendChild(sourcesDiv);
      }

      if (fragments) {
          const fragmentsDiv = document.createElement("div");
          fragmentsDiv.className = "message-fragments";
          const fragmentsTitle = document.createElement("strong");
          fragmentsTitle.textContent = "Фрагменты:";
          fragmentsDiv.appendChild(fragmentsTitle);
          const fragmentsList = document.createElement("ul");
          (Array.isArray(fragments) ? fragments : [fragments]).forEach(frag => {
              const li = document.createElement("li");
              li.textContent = frag || "Нет данных";
              fragmentsList.appendChild(li);
          });
          fragmentsDiv.appendChild(fragmentsList);
          details.appendChild(fragmentsDiv);
      }

      content.appendChild(details);
  }

  msg.appendChild(content);

  if (sender === "bot") {
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
  stored.push({ text, sender, sources, fragments });
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
    console.error("Ошибка загрузки истории:", error);
  }
}
