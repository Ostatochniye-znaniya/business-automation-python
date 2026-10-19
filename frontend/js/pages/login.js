(async function () {
  const status = document.getElementById("login-status");
  const select = document.getElementById("login-user");
  try {
    const users = await apiGet("/auth/dev-users");
    users.forEach((user) =>
      select.add(new Option(`${user.full_name} — ${user.role}`, user.id)),
    );
    status.textContent = users.length
      ? "Локальный стенд разработки. Выберите сотрудника."
      : "Сотрудники ещё не добавлены. Загрузите демоданные или справочник.";
    document.getElementById("login-form").hidden = !users.length;
  } catch (_) {
    status.textContent =
      "Для входа используйте личный кабинет университета. Локальный вход в этом окружении отключён.";
  }
  document
    .getElementById("login-form")
    .addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        await apiPost("/auth/dev-login", { user_id: Number(select.value) });
        location.assign("/pages/workbench.html");
      } catch (error) {
        status.textContent = error.message;
      }
    });
  document.getElementById("logout").addEventListener("click", async () => {
    await apiPost("/auth/logout");
    location.assign("/");
  });
})();
