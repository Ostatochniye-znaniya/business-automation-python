(function () {
  const modal = document.getElementById("discipline-modal");
  const reopenButton = document.getElementById("reopen-button");
  const returnButton = document.getElementById("return-button");
  const clearButton = document.getElementById("clear-button");
  const confirmButton = document.getElementById("confirm-button");
  const status = document.getElementById("discipline-status");
  const dropdowns = Array.from(document.querySelectorAll("[data-dropdown]"));

  const selectedValues = {
    "discipline-one": "Линейная алгебра",
    "discipline-two": "",
  };

  function setDropdownOpen(dropdown, isOpen) {
    const trigger = dropdown.querySelector(".discipline-select");
    const options = dropdown.querySelector(".discipline-options");
    dropdown.classList.toggle("is-open", isOpen);
    trigger.setAttribute("aria-expanded", String(isOpen));
    options.hidden = !isOpen;
  }

  function closeDropdowns(except) {
    dropdowns.forEach((dropdown) => {
      if (dropdown !== except) setDropdownOpen(dropdown, false);
    });
  }

  function updateDropdown(dropdown, value) {
    const id = dropdown.dataset.dropdown;
    const valueElement = dropdown.querySelector(".discipline-select__value");
    selectedValues[id] = value;
    valueElement.textContent = value || "Не выбрано";
    valueElement.classList.toggle("discipline-select__value--placeholder", !value);
    dropdown.querySelectorAll('[role="option"]').forEach((option) => {
      option.setAttribute("aria-selected", String(option.dataset.value === value));
    });
  }

  function openModal() {
    modal.hidden = false;
    reopenButton.hidden = true;
    status.textContent = "";
  }

  function closeModal(message) {
    closeDropdowns();
    modal.hidden = true;
    reopenButton.hidden = false;
    status.textContent = message || "";
    reopenButton.focus();
  }

  dropdowns.forEach((dropdown) => {
    const trigger = dropdown.querySelector(".discipline-select");
    const options = dropdown.querySelector(".discipline-options");

    trigger.addEventListener("click", () => {
      const nextState = !dropdown.classList.contains("is-open");
      closeDropdowns(dropdown);
      setDropdownOpen(dropdown, nextState);
    });

    options.addEventListener("click", (event) => {
      const option = event.target.closest('[role="option"]');
      if (!option) return;
      updateDropdown(dropdown, option.dataset.value);
      setDropdownOpen(dropdown, false);
    });
  });

  clearButton.addEventListener("click", () => {
    dropdowns.forEach((dropdown) => updateDropdown(dropdown, ""));
    closeDropdowns();
  });

  returnButton.addEventListener("click", () => closeModal("Выбор дисциплин отменён."));

  confirmButton.addEventListener("click", () => {
    const selected = Object.values(selectedValues).filter(Boolean);
    closeModal(selected.length ? "Выбор дисциплин закреплён." : "Выберите хотя бы одну дисциплину.");
  });

  reopenButton.addEventListener("click", openModal);

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-dropdown]")) closeDropdowns();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const openedDropdown = dropdowns.find((dropdown) => dropdown.classList.contains("is-open"));
    if (openedDropdown) {
      setDropdownOpen(openedDropdown, false);
      return;
    }
    if (!modal.hidden) closeModal("Выбор дисциплин отменён.");
  });
})();
