    const toast = document.getElementById('toast');
    let currentDirection = 'asc';
    let currentDeleteName = '';

    function notify(message) {
      toast.textContent = message;
      toast.classList.add('show');
      window.setTimeout(() => toast.classList.remove('show'), 2200);
    }

    function openModal(id) {
      document.getElementById(id).classList.add('active');
    }

    function closeModal(id) {
      document.getElementById(id).classList.remove('active');
    }

    // Сортировка таблицы
    document.querySelector('.sort-button').addEventListener('click', function() {
      const tbody = document.getElementById('access-table');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      const arrow = this.querySelector('.sort-arrow');

      currentDirection = currentDirection === 'asc' ? 'desc' : 'asc';
      arrow.textContent = currentDirection === 'asc' ? '↓' : '↑';

      rows.sort((a, b) => {
        const textA = a.cells[0].textContent.trim();
        const textB = b.cells[0].textContent.trim();
        return currentDirection === 'asc'
          ? textA.localeCompare(textB, 'ru')
          : textB.localeCompare(textA, 'ru');
      });

      rows.forEach(row => tbody.appendChild(row));
      notify(`Сортировка по ФИО: ${currentDirection === 'asc' ? 'по возрастанию' : 'по убыванию'}`);
    });

    // Открытие окна редактирования
    document.querySelectorAll('.btn-edit').forEach(btn => {
      btn.addEventListener('click', () => {
        document.getElementById('edit-name').value = btn.dataset.name;
        document.getElementById('edit-position').value = btn.dataset.position;
        document.getElementById('edit-department').value = btn.dataset.department;
        document.getElementById('edit-role').value = btn.dataset.role;
        document.querySelector('.modal-subtitle').textContent = 'Изменение доступа';
        openModal('modal-edit');
      });
    });

    // Открытие окна добавления
    document.getElementById('btn-add-user').addEventListener('click', () => {
      document.getElementById('edit-name').value = '';
      document.getElementById('edit-position').value = 'Преподаватель';
      document.getElementById('edit-department').value = 'ФИТ';
      document.getElementById('edit-role').value = 'Преподаватель';
      document.querySelector('.modal-subtitle').textContent = 'Добавление доступа';
      openModal('modal-edit');
    });

    // Закрытие окна редактирования
    document.querySelector('.modal-icon-close').addEventListener('click', () => {
      closeModal('modal-edit');
    });

    // Сохранение пользователя
    document.getElementById('btn-save-user').addEventListener('click', () => {
      closeModal('modal-edit');
      openModal('modal-success');
    });

    // Открытие окна удаления
    document.querySelectorAll('.btn-delete').forEach(btn => {
      btn.addEventListener('click', () => {
        currentDeleteName = btn.dataset.name;
        openModal('modal-delete');
      });
    });

    // Подтверждение удаления
    document.getElementById('btn-confirm-delete').addEventListener('click', () => {
      closeModal('modal-delete');
      notify(`Пользователь "${currentDeleteName}" удалён`);
    });

    // Отмена удаления
    document.getElementById('btn-cancel-delete').addEventListener('click', () => {
      closeModal('modal-delete');
    });

    // Готово в окне успеха
    document.getElementById('btn-done').addEventListener('click', () => {
      closeModal('modal-success');
    });

    // Отмена в окне успеха
    document.getElementById('btn-cancel-success').addEventListener('click', () => {
      closeModal('modal-success');
    });

    // Закрытие по клику на overlay
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          overlay.classList.remove('active');
        }
      });
    });