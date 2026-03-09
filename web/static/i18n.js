(function () {
  document.documentElement.classList.add('i18n-loading');

  const STORAGE_KEY = 'pw_locale';
  const DEFAULT_LOCALE = 'ru';
  const FALLBACK_LOCALE = 'en';
  const supported = ['ru', 'en'];
  const dictionaries = { ru: {}, en: {} };

  function isLoginPage() {
    return window.location.pathname === '/login';
  }

  function getLocale() {
    if (isLoginPage()) return 'en';
    const saved = localStorage.getItem(STORAGE_KEY);
    return supported.includes(saved) ? saved : DEFAULT_LOCALE;
  }

  function setLocale(locale) {
    if (isLoginPage()) {
      window.__pwLocale = 'en';
      return;
    }
    const next = supported.includes(locale) ? locale : DEFAULT_LOCALE;
    localStorage.setItem(STORAGE_KEY, next);
    window.__pwLocale = next;
  }

  function interpolate(text, params = {}) {
    return String(text).replace(/\{(\w+)\}/g, (_, key) => (params[key] ?? `{${key}}`));
  }

  function t(key, params) {
    const locale = window.__pwLocale || getLocale();
    const localized = dictionaries[locale]?.[key];
    const fallback = dictionaries[FALLBACK_LOCALE]?.[key];
    return interpolate(localized ?? fallback ?? key, params);
  }

  function applyI18n(root = document) {
    root.querySelectorAll('[data-i18n]').forEach((element) => {
      element.textContent = t(element.dataset.i18n);
    });

    root.querySelectorAll('[data-i18n-placeholder]').forEach((element) => {
      element.placeholder = t(element.dataset.i18nPlaceholder);
    });

    root.querySelectorAll('[data-i18n-title]').forEach((element) => {
      element.title = t(element.dataset.i18nTitle);
    });

    root.querySelectorAll('[data-i18n-alt]').forEach((element) => {
      element.alt = t(element.dataset.i18nAlt);
    });

    document.title = t(document.body.dataset.i18nTitle || document.title);
    document.documentElement.lang = window.__pwLocale || getLocale();
  }

  function bindLanguageSwitcher() {
    const toggle = document.getElementById('languageToggle');
    if (!toggle) return;

    const links = toggle.querySelectorAll('[data-locale]');
    const updateActiveLocale = () => {
      const activeLocale = window.__pwLocale || getLocale();
      links.forEach((link) => {
        link.classList.toggle('active', link.dataset.locale === activeLocale);
      });
    };

    updateActiveLocale();
    links.forEach((link) => {
      link.addEventListener('click', (event) => {
        event.preventDefault();
        setLocale(link.dataset.locale);
        applyI18n();
        updateActiveLocale();
        document.dispatchEvent(new CustomEvent('pw:i18n:changed'));
      });
    });

    document.addEventListener('pw:i18n:ready', updateActiveLocale);
    document.addEventListener('pw:i18n:changed', updateActiveLocale);
  }

  async function initI18n() {
    try {
      setLocale(getLocale());
      const [ru, en] = await Promise.all([
        fetch('/static/locales/ru.json').then((r) => r.json()).catch(() => ({})),
        fetch('/static/locales/en.json').then((r) => r.json()).catch(() => ({})),
      ]);
      dictionaries.ru = ru;
      dictionaries.en = en;
      bindLanguageSwitcher();
      applyI18n();
      document.dispatchEvent(new CustomEvent('pw:i18n:ready'));
    } finally {
      await new Promise((resolve) => window.requestAnimationFrame(resolve));
      document.documentElement.classList.remove('i18n-loading');
    }
  }

  window.i18n = { t, applyI18n, setLocale, getLocale };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initI18n, { once: true });
  } else {
    initI18n();
  }
})();
