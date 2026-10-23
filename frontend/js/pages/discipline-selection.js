(function () {
  const groupsBody = document.getElementById("groups-body");
  const dialog = document.getElementById("discipline-selection-dialog");
  const title = document.getElementById("discipline-selection-title");
  const firstSelect = document.getElementById("discipline-selection-first");
  const secondSelect = document.getElementById("discipline-selection-second");
  const error = document.getElementById("discipline-selection-error");
  const status = document.getElementById("discipline-selection-status");
  const confirmedSelections = new Map();
  let selectedGroup = null;

  function setError(message) {
    error.textContent = message;
    error.hidden = !message;
  }

  function openSelection(groupId, groupName) {
    selectedGroup = { id: Number(groupId), name: groupName };
    title.textContent = `Выбор дисциплин для группы ${groupName}`;
    const savedSelection = confirmedSelections.get(groupId) || [];
    firstSelect.value = savedSelection[0] || "";
    secondSelect.value = savedSelection[1] || "";
    status.textContent = "";
    setError("");
    dialog.showModal();
    firstSelect.focus();
  }

  groupsBody.addEventListener("click", function (event) {
    const trigger = event.target.closest('[data-action="select-disciplines"]');
    if (!trigger) {
      return;
    }
    openSelection(trigger.dataset.groupId, trigger.dataset.groupName);
  });

  document.getElementById("discipline-selection-back").addEventListener("click", function () {
    dialog.close();
  });

  document.getElementById("discipline-selection-clear").addEventListener("click", function () {
    firstSelect.value = "";
    secondSelect.value = "";
    setError("");
  });

  document.getElementById("discipline-selection-confirm").addEventListener("click", function () {
    if (!selectedGroup || !firstSelect.value || !secondSelect.value) {
      setError("Выберите две дисциплины перед подтверждением.");
      return;
    }
    if (firstSelect.value === secondSelect.value) {
      setError("Выберите две разные дисциплины.");
      return;
    }

    const disciplineIds = [Number(firstSelect.value), Number(secondSelect.value)];
    const disciplineNames = [firstSelect, secondSelect].map(select =>
      select.options[select.selectedIndex].textContent);
    confirmedSelections.set(String(selectedGroup.id), disciplineIds);
    document.dispatchEvent(new CustomEvent("disciplines-selection-confirmed", {
      detail: {
        groupId: selectedGroup.id,
        groupName: selectedGroup.name,
        disciplineIds,
        disciplineNames,
      },
    }));
    status.textContent = `Для группы ${selectedGroup.name} подтверждено: ${disciplineNames.join(", ")}.`;
    setError("");
    dialog.close();
  });
})();
