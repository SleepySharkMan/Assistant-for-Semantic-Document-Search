document.addEventListener("DOMContentLoaded", () => {
    const toggleButtons = document.querySelectorAll(".toggle-btn");
  
    toggleButtons.forEach(button => {
        button.addEventListener("click", () => {
            // Находим следующий элемент .collapsible-section после заголовка
            const header = button.parentElement;
            const collapsibleSection = header.nextElementSibling;
  
            if (collapsibleSection && collapsibleSection.classList.contains("collapsible-section")) {
                // Переключаем класс collapsed
                collapsibleSection.classList.toggle("collapsed");
  
                // Меняем иконку
                const icon = button.querySelector("i");
                if (collapsibleSection.classList.contains("collapsed")) {
                    icon.classList.remove("fa-chevron-down");
                    icon.classList.add("fa-chevron-up");
                } else {
                    icon.classList.remove("fa-chevron-up");
                    icon.classList.add("fa-chevron-down");
                }
            } else {
                console.error("Collapsible section not found for button:", button);
            }
        });
    });
  });

  