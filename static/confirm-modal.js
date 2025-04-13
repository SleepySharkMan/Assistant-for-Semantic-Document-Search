document.addEventListener("DOMContentLoaded", () => {
    const clearBtn = document.getElementById("clear-btn");
    const modal = document.getElementById("confirm-modal");
    const cancelBtn = document.getElementById("cancel-clear");
  
    if (clearBtn && modal) {
      clearBtn.addEventListener("click", () => {
        modal.style.display = "flex";
      });
    }
  
    if (cancelBtn && modal) {
      cancelBtn.addEventListener("click", () => {
        modal.style.display = "none";
      });
    }
  });
  