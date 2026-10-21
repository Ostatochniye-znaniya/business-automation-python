(function () {
  const userModal = document.getElementById("user-modal");
  const deleteModal = document.getElementById("delete-modal");
  const form = document.getElementById("user-form");
  const formError = document.getElementById("form-error");
  let userToDelete = null;

  function setModalVisibility(modal, visible) {
    modal.hidden = !visible;
    document.body.classList.toggle("modal-open", visible);
  }

  function getField(id) {
    return document.getElementById(id);
  }

  function resetForm() {
    form.reset();
    getField("user-id").value = "";
    getField("user-active").checked = true;
    formError.hidden = true;
    formError.textContent = "";
  }

  function openUserForm(row) {
    resetForm();
    getField("user-modal-title").textContent = row ? "Редактировать участника" : "Добавить участника";

    if (row) {
      getField("user-id").value = row.dataset.userId;
      getField("user-name").value = row.cells[0].textContent.replace(/\s+/g, " ").trim();
      getField("user-department").value = row.cells[1].textContent.trim();
      getField("user-position").value = row.cells[2].textContent.replace(/\s+/g, " ").trim();
      getField("user-start-date").value = toInputDate(row.cells[3].textContent.trim());
      getField("user-end-date").value = toInputDate(row.cells[4].textContent.trim());
      getField("user-active").checked = row.cells[5].textContent.trim() === "Активный";
      getField("user-category").value = row.cells[6].textContent.replace(/\s+/g, " ").trim();
      getField("user-updated").value = row.cells[7].textContent.trim();
    }

    setModalVisibility(userModal, true);
    getField("user-name").focus();
  }

  function toInputDate(value) {
    const parts = value.split(".");
    return parts.length === 3 ? parts[2] + "-" + parts[1] + "-" + parts[0] : "";
  }

  function toDisplayDate(value) {
    const parts = value.split("-");
    return parts.length === 3 ? parts[2] + "." + parts[1] + "." + parts[0] : "—";
  }

  function closeUserForm() {
    setModalVisibility(userModal, false);
  }

  function openDeleteConfirmation(row) {
    userToDelete = row;
    setModalVisibility(deleteModal, true);
  }

  function closeDeleteConfirmation() {
    userToDelete = null;
    setModalVisibility(deleteModal, false);
  }

  function createCell(text) {
    const cell = document.createElement("td");
    cell.textContent = text;
    return cell;
  }

  function addActionButtons(row) {
    const cell = document.createElement("td");
    cell.className = "access-table__actions";
    cell.innerHTML =
      '<button class="row-action row-action--edit" type="button" data-action="edit" aria-label="Редактировать">✎</button>' +
      '<button class="row-action row-action--delete" type="button" data-action="delete" aria-label="Удалить">×</button>';
    row.appendChild(cell);
  }

  function saveUser(event) {
    event.preventDefault();
    if (!form.reportValidity()) {
      return;
    }

    const id = getField("user-id").value;
    const name = getField("user-name").value.trim();
    const row = id ? document.querySelector('tr[data-user-id="' + id + '"]') : document.createElement("tr");
    const values = [
      name,
      getField("user-department").value.trim(),
      getField("user-position").value.trim(),
      toDisplayDate(getField("user-start-date").value),
      toDisplayDate(getField("user-end-date").value),
      getField("user-active").checked ? "Активный" : "Неактивный",
      getField("user-category").value,
      getField("user-updated").value.trim() || "—",
    ];

    row.innerHTML = "";
    values.forEach(function (value) {
      row.appendChild(createCell(value));
    });
    if (!id) {
      row.dataset.userId = String(Date.now());
      document.getElementById("users-table-body").appendChild(row);
    }
    addActionButtons(row);
    document.dispatchEvent(new CustomEvent("user-form-saved", { detail: { id: row.dataset.userId } }));
    closeUserForm();
  }

  document.getElementById("add-user").addEventListener("click", function () {
    openUserForm(null);
  });
  document.getElementById("cancel-user").addEventListener("click", closeUserForm);
  document.getElementById("cancel-delete").addEventListener("click", closeDeleteConfirmation);
  document.getElementById("confirm-delete").addEventListener("click", function () {
    if (userToDelete) {
      userToDelete.remove();
      document.dispatchEvent(new CustomEvent("user-delete-requested", { detail: { id: userToDelete.dataset.userId } }));
    }
    closeDeleteConfirmation();
  });
  form.addEventListener("submit", saveUser);

  document.getElementById("users-table-body").addEventListener("click", function (event) {
    const button = event.target.closest("button[data-action]");
    if (!button) {
      return;
    }
    const row = button.closest("tr");
    if (button.dataset.action === "edit") {
      openUserForm(row);
    } else {
      openDeleteConfirmation(row);
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeUserForm();
      closeDeleteConfirmation();
    }
  });
})();
