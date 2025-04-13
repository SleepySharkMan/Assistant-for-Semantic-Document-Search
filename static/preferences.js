export let preferences = JSON.parse(localStorage.getItem("chatPrefs")) || {
  fontSize: "medium",
  theme: "light",
  contrast: false,
  tts: true,
  panelVisible: true,
};

export function savePreferences() {
  localStorage.setItem("chatPrefs", JSON.stringify(preferences));
}

export function applyPreferences() {
  // Применяем настройки размера шрифта
  document.body.classList.remove("font-small", "font-medium", "font-large");
  document.body.classList.add("font-" + preferences.fontSize);

  // Применяем тему
  document.body.classList.remove("light-theme", "dark-theme", "yellow-theme", "high-contrast");
  if (preferences.theme === "high-contrast") {
    document.body.classList.add("high-contrast");
  } else {
    document.body.classList.add(preferences.theme + "-theme");
  }
  document.body.classList.toggle("high-contrast", preferences.theme === "high-contrast");

  // Обновляем состояние переключателя озвучивания (TTS)
  const ttsToggle = document.getElementById("tts-toggle");
  if (ttsToggle) {
    ttsToggle.checked = preferences.tts;
  }

  // Управляем отображением панели доступности
  const accessibilityWrapper = document.querySelector(".accessibility-wrapper");
  if (accessibilityWrapper) {
    accessibilityWrapper.style.display = preferences.panelVisible ? "flex" : "none";
  }

  // Управляем отображением кнопки открытия панели
  const accessibilityToggle = document.querySelector(".accessibility-toggle");
  if (accessibilityToggle) {
    accessibilityToggle.style.display = preferences.panelVisible ? "none" : "flex";
  }

  // Изменяем отступ и высоту контейнера чата
  const container = document.querySelector(".container");
  if (container) {
    if (preferences.panelVisible) {
      container.style.marginTop = "80px";
      container.style.height = "calc(100% - 80px)";
    } else {
      container.style.marginTop = "0";
      container.style.height = "100%";
    }
  }
}
