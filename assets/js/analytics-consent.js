(() => {
  "use strict";

  const MEASUREMENT_ID = "G-YSFEEJSTJ3";
  const STORAGE_KEY = "cruxresolve.analyticsConsent.v1";
  const GRANTED = "granted";
  const DENIED = "denied";

  const banner = document.querySelector("[data-analytics-consent]");
  const acceptButton = document.querySelector("[data-analytics-accept]");
  const declineButton = document.querySelector("[data-analytics-decline]");
  const settingsButtons = document.querySelectorAll("[data-privacy-settings]");

  if (!banner || !acceptButton || !declineButton) return;

  const readConsent = () => {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (_error) {
      return null;
    }
  };

  const writeConsent = (value) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch (_error) {
      // Consent still applies for the current page when storage is unavailable.
    }
  };

  const showBanner = (moveFocus = false) => {
    banner.hidden = false;
    if (moveFocus) acceptButton.focus();
  };

  const hideBanner = () => {
    banner.hidden = true;
  };

  const loadGoogleAnalytics = () => {
    if (window.__cruxResolveGa4Loaded) return;
    window.__cruxResolveGa4Loaded = true;

    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function gtag() {
      window.dataLayer.push(arguments);
    };

    window.gtag("js", new Date());
    window.gtag("config", MEASUREMENT_ID, {
      allow_google_signals: false,
      allow_ad_personalization_signals: false
    });

    const script = document.createElement("script");
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(MEASUREMENT_ID)}`;
    script.dataset.cruxGa4 = "true";
    document.head.appendChild(script);
  };

  const clearGoogleAnalyticsCookies = () => {
    document.cookie.split(";").forEach((entry) => {
      const name = entry.split("=")[0].trim();
      if (!name.startsWith("_ga")) return;

      const expiry = "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
      document.cookie = `${name}${expiry}`;
      document.cookie = `${name}${expiry}; domain=${window.location.hostname}`;
      document.cookie = `${name}${expiry}; domain=.cruxresolve.com`;
    });
  };

  acceptButton.addEventListener("click", () => {
    writeConsent(GRANTED);
    hideBanner();
    loadGoogleAnalytics();
  });

  declineButton.addEventListener("click", () => {
    const analyticsWasLoaded = Boolean(window.__cruxResolveGa4Loaded);
    writeConsent(DENIED);
    clearGoogleAnalyticsCookies();
    hideBanner();

    if (analyticsWasLoaded) {
      window.location.reload();
    }
  });

  settingsButtons.forEach((button) => {
    button.addEventListener("click", () => showBanner(true));
  });

  const savedConsent = readConsent();
  if (savedConsent === GRANTED) {
    loadGoogleAnalytics();
  } else if (savedConsent !== DENIED) {
    showBanner(false);
  }
})();
