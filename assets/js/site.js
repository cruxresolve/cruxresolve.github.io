(() => {
  "use strict";

  const CAMPAIGN_STORAGE_KEY = "cruxresolve.campaign.v1";
  const CAMPAIGN_FIELDS = [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term"
  ];

  const track = (eventName, parameters = {}) => {
    if (typeof window.cruxTrack === "function") {
      window.cruxTrack(eventName, parameters);
    }
  };

  const slugify = (value) => String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "") || "website";

  const readCampaign = () => {
    const params = new URLSearchParams(window.location.search);
    const currentCampaign = {};

    CAMPAIGN_FIELDS.forEach((field) => {
      const value = params.get(field);
      if (value) currentCampaign[field] = value.slice(0, 120);
    });

    if (Object.keys(currentCampaign).length) {
      try {
        window.sessionStorage.setItem(
          CAMPAIGN_STORAGE_KEY,
          JSON.stringify(currentCampaign)
        );
      } catch (_error) {
        // Campaign tracking still works on the current page without storage.
      }
      return currentCampaign;
    }

    try {
      const saved = window.sessionStorage.getItem(CAMPAIGN_STORAGE_KEY);
      return saved ? JSON.parse(saved) : {};
    } catch (_error) {
      return {};
    }
  };

  const campaign = readCampaign();

  const clickContext = (link) => {
    const section = link.closest("section");
    let ctaLocation = "page";

    if (section) {
      if (section.id) {
        ctaLocation = slugify(section.id);
      } else if (section.classList.contains("hero")) {
        ctaLocation = "hero";
      }
    }

    return {
      page_path: window.location.pathname,
      page_title: document.title,
      cta_location: ctaLocation,
      ...campaign
    };
  };

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

  document.querySelectorAll('a[href*="apps.apple.com"][href*="id6778061607"], a[href="/go/ghosttune.html"]').forEach((link) => {
    link.addEventListener("click", () => {
      track("ghosttune_app_store_click", {
        product: "GhostTune",
        destination: "app_store",
        ...clickContext(link)
      });
    });
  });

  document.querySelectorAll('a[href*="buy.stripe.com"], a[href="/go/ghostbridge-checkout.html"]').forEach((link) => {
    link.addEventListener("click", () => {
      const context = clickContext(link);

      track("ghostbridge_checkout_click", {
        product: "GhostBridge GB-01",
        destination: "stripe_checkout",
        currency: "USD",
        value: 89,
        ...context
      });

      track("begin_checkout", {
        currency: "USD",
        value: 89,
        items: [{
          item_id: "ghostbridge",
          item_name: "GhostBridge",
          price: 89,
          quantity: 1
        }],
        ...context
      });
    });
  });

  document.querySelectorAll('a[href="mailto:support@cruxresolve.com"]').forEach((link) => {
    link.addEventListener("click", () => {
      track("contact_support", {
        contact_method: "email",
        page_path: window.location.pathname
      });
    });
  });

  document.querySelectorAll('select[name="interest"]').forEach((select) => {
    select.addEventListener("change", () => {
      if (!select.value) return;
      track("select_content", {
        content_type: "ghosttune_interest",
        content_id: slugify(select.value)
      });
    });
  });

  document.querySelectorAll("form[data-async-form]").forEach((form) => {
    const statusId = form.getAttribute("aria-describedby");
    const status = statusId ? document.getElementById(statusId) : null;
    const submit = form.querySelector('button[type="submit"]');

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const formName =
        formData.get("form_name") ||
        formData.get("product") ||
        formData.get("subject") ||
        "website form";
      const interest = formData.get("interest");

      if (status) {
        status.dataset.state = "";
        status.textContent = "Submitting…";
      }
      if (submit) submit.disabled = true;

      try {
        const response = await fetch(form.action, {
          method: form.method || "POST",
          body: formData,
          headers: { Accept: "application/json" }
        });

        if (!response.ok) throw new Error(`Request failed with ${response.status}`);

        track("generate_lead", {
          lead_type: slugify(formName),
          ...(interest ? { interest_type: slugify(interest) } : {})
        });

        form.reset();
        if (status) {
          status.dataset.state = "success";
          status.textContent = "Thank you. Your request has been submitted.";
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
