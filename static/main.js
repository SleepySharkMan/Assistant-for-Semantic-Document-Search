import { addMessage, clearMessages, showLoadingIndicator, hideLoadingIndicator } from './messages.js';
import { speakText, startRecording } from './speech.js';
import { preferences, applyPreferences } from './preferences.js';
import './accessibility.js';
import './confirm-modal.js';

let userInput;
let userId = getOrCreateUserId();
let userHasInteracted = false;

document.addEventListener("DOMContentLoaded", () => {
  console.log("User ID:", userId);

  const sendBtn = document.getElementById("send-btn");
  const micBtn = document.getElementById("mic-btn");
  const confirmBtn = document.getElementById("confirm-clear");
  const modal = document.getElementById("confirm-modal");

  userInput = document.getElementById("user-input");

  applyPreferences();
  loadServerMessages();

  // Отслеживаем первое взаимодействие пользователя
  const markUserInteraction = () => {
    if (!userHasInteracted) {
      userHasInteracted = true;
      console.log("Пользователь взаимодействовал - TTS теперь доступен");
    }
  };

  sendBtn.addEventListener("click", () => {
    markUserInteraction();
    sendMessage();
  });

  micBtn.addEventListener("click", () => {
    markUserInteraction();
    startRecording();
  });

  userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      markUserInteraction();
      sendMessage();
    }
  });

  // Также отмечаем взаимодействие при любом клике или нажатии клавиши
  document.addEventListener("click", markUserInteraction, { once: false });
  document.addEventListener("keydown", markUserInteraction, { once: false });

  if (confirmBtn) {
    confirmBtn.addEventListener("click", () => {
      clearMessages();

      fetch("/api/history", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId })
      }).catch((err) => {
        console.error("Ошибка при удалении истории на сервере:", err);
      });

      if (modal) modal.style.display = "none";
    });
  }

  document.addEventListener("click", (e) => {
    const playBtn = e.target.closest(".play-audio-btn");
    if (playBtn) {
      const message = playBtn.closest(".message");
      const text = message?.querySelector("p")?.textContent;
      if (text) speakText(text, playBtn);
    }
  });
});

function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  // Добавляем сообщение пользователя
  addMessage(text, "user");
  userInput.value = "";

  // Показываем индикатор загрузки
  showLoadingIndicator();

  const sourceToggle = document.getElementById("source-toggle");
  const fragmentsToggle = document.getElementById("fragments-toggle");
  const showSourceInfo = sourceToggle ? sourceToggle.checked : false;
  const showTextFragments = fragmentsToggle ? fragmentsToggle.checked : false;

  fetch("/api/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
          message: text,
          user_id: userId,
          show_source_info: showSourceInfo,
          show_text_fragments: showTextFragments
      })
  })
      .then((res) => res.json())
      .then((data) => {
          // Скрываем индикатор загрузки
          hideLoadingIndicator();
          
          // Добавляем ответ бота
          addMessage(data.answer, "bot", data.source, data.fragments);
          
          // Озвучиваем ответ, если включено TTS и пользователь взаимодействовал
          if (preferences.tts && userHasInteracted) {
              // Небольшая задержка, чтобы сообщение успело отрендериться
              setTimeout(() => {
                  speakText(data.answer);
              }, 100);
          } else if (preferences.tts && !userHasInteracted) {
              console.warn("TTS отключен - требуется взаимодействие пользователя");
          }
      })
      .catch((err) => {
          // Скрываем индикатор загрузки в случае ошибки
          hideLoadingIndicator();
          
          console.error(err);
          addMessage("Ошибка при получении ответа", "bot");
      });
}

function loadServerMessages() {
  fetch(`/api/history?user_id=${encodeURIComponent(userId)}`)
    .then((res) => res.json())
    .then((data) => {
      if (Array.isArray(data.messages)) {
        data.messages.forEach(msg => addMessage(msg.text, msg.sender));
      }
    })
    .catch(err => {
      console.error("Ошибка загрузки истории:", err);
    });
}

function getOrCreateUserId() {
  const storageKey = "userId";
  let userId = localStorage.getItem(storageKey);

  if (!userId) {
    userId = crypto.randomUUID();
    localStorage.setItem(storageKey, userId);
  }

  return userId;
}