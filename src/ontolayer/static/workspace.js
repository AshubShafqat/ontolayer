"use strict";

// Shared behaviors apply to dynamic views without replacing their existing flows.
const preferences = {
  get(key, fallback) {
    try {
      return localStorage.getItem(key) || fallback;
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* private browsing */
    }
  },
};
function setTheme(value) {
  preferences.set(`ontolayer-theme-${state.data?.actor.id || "signin"}`, value);
  document.documentElement.dataset.theme =
    value === "system"
      ? matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      : value;
}
function enhance() {
  document.querySelectorAll(".table-wrap").forEach((el) => {
    el.tabIndex = 0;
    el.setAttribute("role", "region");
    el.setAttribute("aria-label", "Scrollable data table");
  });
  const sidebar = $(".sidebar");
  if (sidebar && !$("#workspace-preferences")) {
    sidebar.insertAdjacentHTML(
      "beforeend",
      `<div id="workspace-preferences"><label for="theme">Appearance</label><select id="theme"><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select><button class="btn" data-action="help">Keyboard help</button></div>`,
    );
    $("#theme").value = preferences.get(
      `ontolayer-theme-${state.data.actor.id}`,
      "system",
    );
    setTheme($("#theme").value);
    sidebar.insertAdjacentHTML(
      "afterbegin",
      '<button id="menu-toggle" class="btn" aria-expanded="false" aria-controls="workspace-nav">Menu</button>',
    );
    $(".nav").id = "workspace-nav";
  }
  const status = $(".top-actions > .status");
  if (status) {
    const text = navigator.onLine ? "Connected" : "Offline";
    if (status.textContent.trim() !== text) status.textContent = text;
  }
}
function modal(title, content) {
  $("#dialog")?.remove();
  const dialog = document.createElement("dialog");
  dialog.id = "dialog";
  dialog.setAttribute("aria-labelledby", "dialog-title");
  dialog.innerHTML = `<h2 id="dialog-title">${esc(title)}</h2>${content}<form method="dialog"><button class="btn">Close</button></form>`;
  document.body.append(dialog);
  dialog.showModal();
}
document.addEventListener("change", (event) => {
  if (event.target.id === "theme") setTheme(event.target.value);
});
document.addEventListener("click", (event) => {
  const el = event.target.closest("button, a");
  if (!el) return;
  if (el.id === "menu-toggle") {
    const open = el.getAttribute("aria-expanded") !== "true";
    el.setAttribute("aria-expanded", String(open));
    $(".sidebar").classList.toggle("menu-open", open);
  }
  if (el.dataset.nav) {
    $(".sidebar")?.classList.remove("menu-open");
    $("#menu-toggle")?.setAttribute("aria-expanded", "false");
  }
  if (el.dataset.action === "help")
    modal(
      "Keyboard shortcuts",
      "<dl><dt>Alt + K</dt><dd>Search the workspace</dd><dt>Ctrl / Command + Enter</dt><dd>Run the guided query</dd><dt>Alt + T</dt><dd>Toggle theme</dd><dt>Escape</dt><dd>Close a dialog</dd></dl>",
    );
});
document.addEventListener("keydown", (event) => {
  if (event.altKey && event.key.toLowerCase() === "t") {
    event.preventDefault();
    setTheme(
      document.documentElement.dataset.theme === "dark" ? "light" : "dark",
    );
    if ($("#theme")) $("#theme").value = document.documentElement.dataset.theme;
  }
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    $("#query-form")?.requestSubmit();
  }
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  if ($("#theme")?.value === "system") setTheme("system");
});
window.addEventListener("online", enhance);
window.addEventListener("offline", enhance);
let enhancing = false;
new MutationObserver(() => {
  if (enhancing) return;
  enhancing = true;
  requestAnimationFrame(() => {
    enhance();
    enhancing = false;
  });
}).observe($("#app"), { childList: true, subtree: true });
setTheme(preferences.get("ontolayer-theme-signin", "system"));
