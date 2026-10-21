const SECTIONS = [
  { title: "Главная", href: "/" },
  { title: "Приказы", href: "/pages/orders.html" },
  { title: "Списки <br>рекомендуемых <br>групп", href: "/pages/groups.html" },
  { title: "Отчёты", href: "/pages/reports.html" },
  { title: "Настройки <br>доступа", href: "/pages/access.html" },
  {title: "Настройки <br>системы", href: "/pages/options.html" }
];

const THEME_KEY = "theme";
function currentPath() {
  const path = window.location.pathname.replace(/index\.html$/, "");
  return path === "" ? "/" : path;
}
function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem(THEME_KEY, theme); } catch (_) {}
}
function renderSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  const active = currentPath() === "/pages/optionsDate.html" ? "/pages/options.html" : currentPath();
  const links = SECTIONS.map(function (section) {
    const isActive = section.href === active;
    const modifier = isActive ? " sidebar__link--active" : "";
    const dot = isActive ? '<span class="sidebar__dot" aria-hidden="true"></span>' : "";
    return '<a class="sidebar__link' + modifier + '" href="' + section.href + '"' + (isActive ? ' aria-current="page"' : '') + '>' + dot + '<span>' + section.title + '</span></a>';
  }).join("");
  sidebar.innerHTML =
    '<div class="sidebar__brand"><img class="sidebar__logo" id="sidebar-logo" src="../assets/logo_light.png" alt="Московский Политех" /></div>' +
    '<div class="sidebar__project">Проверка<br>остаточных знаний</div>' +
    '<div class="sidebar__profile"><div class="sidebar__avatar" aria-hidden="true"></div><div class="sidebar__profile-name">Иванов<br>Иван Иванович</div></div>' +
    '<nav class="sidebar__nav" aria-label="Основная навигация">' + links + '</nav>' +
    '<div class="sidebar__footer"><button class="button button--secondary" type="button" id="theme-toggle"></button></div>';
  const toggle = document.getElementById("theme-toggle");
  const logo = document.getElementById("sidebar-logo");
  function updateThemeButton() {
    const dark = currentTheme() === "dark";
    toggle.textContent = dark ? "Светлая тема" : "Тёмная тема";
    logo.src = dark ? "../assets/logo_dark.png" : "../assets/logo_light.png";
  }
  updateThemeButton();
  toggle.addEventListener("click", function () {
    applyTheme(currentTheme() === "dark" ? "light" : "dark");
    updateThemeButton();
  });
}
renderSidebar();
