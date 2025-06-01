let currentAudio = null;
let currentButton = null;

/**
 * Воспроизводит или останавливает озвучивание текста при клике на кнопку.
 * @param {string} text - Текст для озвучивания.
 * @param {HTMLElement|null} button - Кнопка, с которой было взаимодействие.
 */
export function speakText(text, button = null) {
  if (!button) return;

  // Если кнопка уже заблокирована — выходим
  if (button.disabled) return;

  // Если нажата та же — остановить
  if (currentAudio && button === currentButton) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentButton.classList.remove("playing");
    currentAudio = null;
    currentButton = null;
    return;
  }

  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentButton?.classList.remove("playing");
  }

  button.disabled = true;

  fetch("/api/text-to-speech", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  })
    .then(res => res.blob())
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      currentAudio = audio;
      currentButton = button;
      currentButton.classList.add("playing");

      audio.play().then(() => {
        button.disabled = false;
      });

      audio.onended = () => {
        currentButton?.classList.remove("playing");
        currentAudio = null;
        currentButton = null;
      };
    })
    .catch(err => {
      console.error("Ошибка озвучивания:", err);
      button.disabled = false;
    });
}

/**
 * Останавливает текущее озвучивание, если оно есть.
 */
export function stopSpeech() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
    currentButton?.classList.remove("playing");
    currentButton = null;
  }
}

/**
 * Запускает запись голоса, отправляет на сервер и вставляет результат в поле ввода.
 */
export function startRecording() {
  const userInput = document.getElementById("user-input");

  navigator.mediaDevices.getUserMedia({ audio: true })
    .then((stream) => {
      const mediaRecorder = new MediaRecorder(stream);
      const audioChunks = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
        const formData = new FormData();
        formData.append("audio", audioBlob, "speech.wav");

        fetch("/api/speech-to-text", {
          method: "POST",
          body: formData
        })
          .then((res) => res.json())
          .then((data) => {
            if (data.text) {
              userInput.value = data.text;
            }
          })
          .catch((err) => {
            console.error("Ошибка при распознавании речи:", err);
          });
      };

      mediaRecorder.start();
      setTimeout(() => mediaRecorder.stop(), 4000);
    })
    .catch((err) => {
      console.error("Ошибка при доступе к микрофону:", err);
    });
}