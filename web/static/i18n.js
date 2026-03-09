(function () {
  const STORAGE_KEY = 'pw_locale';
  const DEFAULT_LOCALE = 'ru';
  const FALLBACK_LOCALE = 'en';
  const supported = ['ru', 'en'];
  const dictionaries = { ru: {}, en: {} };

  function getLocale() {
    const saved = localStorage.getItem(STORAGE_KEY);
    return supported.includes(saved) ? saved : DEFAULT_LOCALE;
  }

  function setLocale(locale) {
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
    const switcher = document.getElementById('languageSwitcher');
    if (!switcher) return;
    switcher.value = window.__pwLocale || getLocale();
    switcher.addEventListener('change', () => {
      setLocale(switcher.value);
      applyI18n();
      document.dispatchEvent(new CustomEvent('pw:i18n:changed'));
    });
  }

  async function initI18n() {
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
  }

  window.i18n = { t, applyI18n, setLocale, getLocale };
  document.addEventListener('DOMContentLoaded', initI18n);
})();
