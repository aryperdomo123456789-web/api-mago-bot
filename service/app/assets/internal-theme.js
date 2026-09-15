(() => {
  "use strict";

  const STORAGE_KEY = "mago-internal-theme";
  const validThemes = new Set(["dark", "light"]);

  const updateControls = (theme) => {
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      const nextTheme = theme === "dark" ? "light" : "dark";
      button.setAttribute("aria-label", nextTheme === "light" ? "Ativar tema claro" : "Ativar tema escuro");
      button.setAttribute("title", nextTheme === "light" ? "Ativar tema claro" : "Ativar tema escuro");
      button.dataset.themeValue = nextTheme;
      const icon = button.querySelector("[data-theme-icon]");
      const label = button.querySelector("[data-theme-label]");
      if (icon) icon.textContent = nextTheme === "light" ? "☼" : "☾";
      if (label) label.textContent = nextTheme === "light" ? "Claro" : "Escuro";
    });
  };

  const apply = (theme, persist = true) => {
    const resolved = validThemes.has(theme) ? theme : "dark";
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme = resolved;
    if (persist) window.localStorage?.setItem(STORAGE_KEY, resolved);
    updateControls(resolved);
    window.dispatchEvent(new CustomEvent("mago:themechange", { detail: { theme: resolved } }));
  };

  const stored = window.localStorage?.getItem(STORAGE_KEY);
  apply(validThemes.has(stored) ? stored : "dark", false);

  const init = () => {
    updateControls(document.documentElement.dataset.theme || "dark");
    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-theme-toggle]");
      if (!button) return;
      apply(button.dataset.themeValue || "light");
    });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
  window.MagoTheme = { apply, get: () => document.documentElement.dataset.theme || "dark" };
})();
