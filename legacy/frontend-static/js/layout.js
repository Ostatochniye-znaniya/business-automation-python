const SECTIONS = [
  { title: "Рабочие процессы", href: "/pages/workbench.html" },
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
    '<div class="sidebar__brand"><img class="sidebar__logo sidebar__logo--light" src="/assets/logo_light.png" alt="Московский Политех"><img class="sidebar__logo sidebar__logo--dark" src="/assets/logo_dark.png" alt="Московский Политех"></div>' +
    '<div class="sidebar__divider"></div>' +
    '<div class="sidebar__project">Проверка<br>остаточных знаний</div>' +
    '<div class="sidebar__profile"><div class="sidebar__avatar" aria-hidden="true"></div><div class="sidebar__profile-name"><a href="/pages/login.html">Войти в систему</a></div></div>' +
    '<nav class="sidebar__nav" aria-label="Основная навигация">' + links + '</nav>' +
    '<div class="sidebar__footer"><span class="sidebar__theme-label" id="theme-label">Тёмная тема</span><label class="sidebar__theme-switch" aria-label="Переключить тему"><input type="checkbox" id="theme-toggle" aria-label="Переключить тему"><span class="sidebar__theme-slider"><span class="sidebar__theme-knob"></span></span></label></div>';
  const toggle = document.getElementById("theme-toggle");
  const label = document.getElementById("theme-label");
  function syncThemeControl() {
    const dark = currentTheme() === "dark";
    toggle.checked = dark;
    label.textContent = dark ? "Светлая тема" : "Тёмная тема";
  }
  syncThemeControl();
  toggle.addEventListener("change", function () {
    applyTheme(toggle.checked ? "dark" : "light");
    syncThemeControl();
  });
}
renderSidebar();
if (typeof document.addEventListener === 'function' && typeof fetch === 'function') {
  document.addEventListener('DOMContentLoaded', async () => {
    try {
      const response = await fetch((window.APP_CONFIG?.apiBase || '/api') + '/auth/me');
      if (!response.ok) return;
      const user = await response.json();
      const profile = document.querySelector('.sidebar__profile-name');
      if (profile) profile.textContent = user.full_name;
    } catch (_) { /* Login link remains available when the API is unavailable. */ }
  });
}
