const SECTIONS = [
  { title: "Главная", href: "/" },
  { title: "Приказы", href: "/pages/orders.html" },
  { title: "Списки рекомендуемых групп", href: "/pages/groups.html" },
  { title: "Отчёты", href: "/pages/reports.html" },
  { title: "Настройки доступа", href: "/pages/access.html" },
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
  localStorage.setItem(THEME_KEY, theme);
}

function themeButtonTitle() {
  return currentTheme() === "dark" ? "Светлая тема" : "Тёмная тема";
}

function renderSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) {
    return;
  }

  const active = currentPath();
  const links = SECTIONS.map(function (section) {
    const modifier = section.href === active ? " sidebar__link--active" : "";
    return (
      '<a class="sidebar__link' + modifier + '" href="' + section.href + '">' +
      section.title +
      "</a>"
    );
  }).join("");

  sidebar.innerHTML =
    '<div class="sidebar__title">Остаточные знания</div>' +
    '<nav class="sidebar__nav">' + links + "</nav>" +
    '<div class="sidebar__footer">' +
    '<button class="button button--secondary" type="button" id="theme-toggle"></button>' +
    "</div>";

  const toggle = document.getElementById("theme-toggle");
  toggle.textContent = themeButtonTitle();
  toggle.addEventListener("click", function () {
    applyTheme(currentTheme() === "dark" ? "light" : "dark");
    toggle.textContent = themeButtonTitle();
  });
}

renderSidebar();
