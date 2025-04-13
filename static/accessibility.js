import { preferences, savePreferences, applyPreferences } from './preferences.js';

document.addEventListener("DOMContentLoaded", () => {
  // Получаем элементы управления доступностью
  const fontSizeBtns = document.querySelectorAll(".font-size-btn");
  const themeBtns = document.querySelectorAll(".theme-btn");
  const ttsToggle = document.getElementById("tts-toggle");
  const normalBtn = document.querySelector(".normal-version-btn");
  const closeBtn = document.querySelector(".close-panel-btn");
  const accessibilityToggle = document.querySelector(".accessibility-toggle");

  // Применяем сохранённые настройки при загрузке страницы
  applyPreferences();

  // Обработчик для изменения размера шрифта
  fontSizeBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      fontSizeBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      if (btn.classList.contains("small")) {
        preferences.fontSize = "small";
      } else if (btn.classList.contains("large")) {
        preferences.fontSize = "large";
      } else {
        preferences.fontSize = "medium";
      }
      savePreferences();
      applyPreferences();
    });
  });

  // Обработчик для выбора темы
  themeBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      themeBtns.forEach(b => b.classList.remove("active-theme"));
      btn.classList.add("active-theme");
      if (btn.classList.contains("dark-theme")) {
        preferences.theme = "dark";
      } else if (btn.classList.contains("yellow-theme")) {
        preferences.theme = "yellow";
      } else if (btn.classList.contains("high-contrast")) {
        preferences.theme = "high-contrast";
      } else {
        preferences.theme = "light";
      }
      savePreferences();
      applyPreferences();
    });
  });

  // Обработчик переключателя озвучивания (TTS)
  if (ttsToggle) {
    ttsToggle.addEventListener("change", () => {
      preferences.tts = ttsToggle.checked;
      savePreferences();
    });
  }

  // Обработчик для кнопки "Обычная версия сайта" (сброс настроек)
  if (normalBtn) {
    normalBtn.addEventListener("click", () => {
      preferences.fontSize = "medium";
      preferences.theme = "light";
      preferences.tts = true;
      preferences.panelVisible = true;
      savePreferences();
      applyPreferences();

      // Обновляем активное состояние для кнопок размера шрифта
      fontSizeBtns.forEach(btn => {
        btn.classList.remove("active");
        if (btn.classList.contains("medium")) {
          btn.classList.add("active");
        }
      });

      // Обновляем активное состояние для кнопок темы
      themeBtns.forEach(btn => {
        btn.classList.remove("active-theme");
        if (btn.classList.contains("light-theme")) {
          btn.classList.add("active-theme");
        }
      });
    });
  }

  // Обработчик для кнопки закрытия панели доступности
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      preferences.panelVisible = false;
      savePreferences();
      applyPreferences();
    });
  }

  // Обработчик для кнопки открытия панели доступности (toggle)
  if (accessibilityToggle) {
    accessibilityToggle.addEventListener("click", () => {
      preferences.panelVisible = true;
      savePreferences();
      applyPreferences();
    });
  }
});
