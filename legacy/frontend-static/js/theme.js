(function () {
  try {
    const theme = localStorage.getItem("theme") || localStorage.getItem("app-theme");
    document.documentElement.dataset.theme = theme === "dark" ? "dark" : "light";
  } catch (_) {
    document.documentElement.dataset.theme = "light";
  }
})();
