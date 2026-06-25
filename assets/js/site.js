(() => {
  "use strict";

  const button = document.querySelector("[data-menu-button]");
  const menu = document.querySelector("[data-mobile-menu]");

  const closeMenu = (restoreFocus = false) => {
    if (!button || !menu) return;
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-label", "Open menu");
    menu.dataset.open = "false";
    menu.hidden = true;
    if (restoreFocus) button.focus();
  };

  const openMenu = () => {
    if (!button || !menu) return;
    button.setAttribute("aria-expanded", "true");
    button.setAttribute("aria-label", "Close menu");
    menu.hidden = false;
    menu.dataset.open = "true";
    const firstLink = menu.querySelector("a");
    if (firstLink) firstLink.focus();
  };

  if (button && menu) {
    closeMenu();
    button.addEventListener("click", () => {
      const isOpen = button.getAttribute("aria-expanded") === "true";
      isOpen ? closeMenu(true) : openMenu();
    });
    menu.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => closeMenu(false));
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && button.getAttribute("aria-expanded") === "true") {
        closeMenu(true);
      }
    });
    document.addEventListener("click", (event) => {
      if (
        button.getAttribute("aria-expanded") === "true" &&
        !menu.contains(event.target) &&
        !button.contains(event.target)
      ) {
        closeMenu(false);
      }
    });
  }

  document.querySelectorAll("[data-faq-button]").forEach((faqButton) => {
    const panelId = faqButton.getAttribute("aria-controls");
    const panel = panelId ? document.getElementById(panelId) : null;
    if (!panel) return;

    faqButton.addEventListener("click", () => {
      const expanded = faqButton.getAttribute("aria-expanded") === "true";
      faqButton.setAttribute("aria-expanded", String(!expanded));
      panel.hidden = expanded;
    });
  });

  document.querySelectorAll("form[data-async-form]").forEach((form) => {
    const statusId = form.getAttribute("aria-describedby");
    const status = statusId ? document.getElementById(statusId) : null;
    const submit = form.querySelector('button[type="submit"]');

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (status) {
        status.dataset.state = "";
        status.textContent = "Submitting…";
      }
      if (submit) submit.disabled = true;

      try {
        const response = await fetch(form.action, {
          method: form.method || "POST",
          body: new FormData(form),
          headers: { Accept: "application/json" }
        });

        if (!response.ok) throw new Error(`Request failed with ${response.status}`);

        form.reset();
        if (status) {
          status.dataset.state = "success";
          status.textContent = "Thank you. Your email has been added.";
        }
      } catch (error) {
        if (status) {
          status.dataset.state = "error";
          status.textContent = "We could not submit the form. Please email support@cruxresolve.com.";
        }
      } finally {
        if (submit) submit.disabled = false;
      }
    });
  });
})();
