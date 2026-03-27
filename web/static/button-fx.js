(() => {
  const AUTO_BUTTON_SELECTOR = [
    'button',
    'input[type="button"]',
    'input[type="submit"]'
  ].join(',');
  const OPT_IN_SELECTOR = '[data-button-fx="on"]';
  const SAFE_CHILD_TAGS = new Set(['SPAN', 'SVG', 'IMG']);

  function isElementButtonLike(element) {
    if (!(element instanceof HTMLElement)) return false;
    if (element.dataset.buttonFx === 'off') return false;
    return element.matches(AUTO_BUTTON_SELECTOR) || element.matches(OPT_IN_SELECTOR);
  }

  function isWrapped(element) {
    return Array.from(element.children).some((child) => child.classList.contains('fx-btn__content'));
  }

  function hasSafeStructureForWrap(button) {
    if (button.hasAttribute('aria-haspopup')) return false;
    const elementChildren = Array.from(button.children);
    if (elementChildren.length === 0) return true;
    if (elementChildren.length > 3) return false;
    return elementChildren.every((child) => SAFE_CHILD_TAGS.has(child.tagName));
  }

  function createIcon(markup) {
    const wrapper = document.createElement('span');
    wrapper.className = 'fx-btn__icon';
    wrapper.innerHTML = markup;
    return wrapper;
  }

  function ensureStructure(button) {
    if (!(button instanceof HTMLElement)) return;
    // Inputs cannot host overlay children; they intentionally stay visual-only.
    if (button.tagName === 'INPUT') return;
    if (isWrapped(button)) return;
    if (!hasSafeStructureForWrap(button)) {
      // Keep state/ripple API but avoid DOM rewrites for complex button internals.
      button.dataset.fxBtnOverlay = 'visual-only';
      return;
    }

    const content = document.createElement('span');
    content.className = 'fx-btn__content';

    const defaultState = document.createElement('span');
    defaultState.className = 'fx-btn__state fx-btn__state--default';

    while (button.firstChild) {
      defaultState.appendChild(button.firstChild);
    }

    const loadingState = document.createElement('span');
    loadingState.className = 'fx-btn__state fx-btn__state--loading';
    loadingState.setAttribute('aria-hidden', 'true');
    const spinner = document.createElement('span');
    spinner.className = 'fx-btn__spinner';
    spinner.setAttribute('aria-hidden', 'true');
    loadingState.appendChild(spinner);

    const successState = document.createElement('span');
    successState.className = 'fx-btn__state fx-btn__state--success';
    successState.setAttribute('aria-hidden', 'true');
    successState.appendChild(createIcon('<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4.5 10.5L8.2 14.2L15.5 6.8" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"></path></svg>'));

    const errorState = document.createElement('span');
    errorState.className = 'fx-btn__state fx-btn__state--error';
    errorState.setAttribute('aria-hidden', 'true');
    errorState.appendChild(createIcon('<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M6 6L14 14M14 6L6 14" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"></path></svg>'));

    const glow = document.createElement('span');
    glow.className = 'fx-btn__glow';
    glow.setAttribute('aria-hidden', 'true');
    const ring = document.createElement('span');
    ring.className = 'fx-btn__ring';
    ring.setAttribute('aria-hidden', 'true');

    content.append(defaultState, loadingState, successState, errorState);
    button.append(glow, ring, content);
  }

  function createRipple(button, event) {
    if (!(button instanceof HTMLElement)) return;
    if (button.dataset.state === 'loading' || button.disabled || button.getAttribute('aria-disabled') === 'true') return;

    const oldRipple = button.querySelector('.fx-btn__ripple');
    if (oldRipple) oldRipple.remove();

    const rect = button.getBoundingClientRect();
    const ripple = document.createElement('span');
    ripple.className = 'fx-btn__ripple';

    const size = Math.max(rect.width, rect.height) * 0.9;
    ripple.style.width = `${size}px`;
    ripple.style.height = `${size}px`;
    ripple.style.left = `${event.clientX - rect.left}px`;
    ripple.style.top = `${event.clientY - rect.top}px`;

    button.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove(), { once: true });
  }

  function setButtonState(button, state) {
    if (!(button instanceof HTMLElement)) return;

    if (!state) {
      if (button.dataset.fxBtnTempDisabled === 'true') {
        button.disabled = false;
        delete button.dataset.fxBtnTempDisabled;
      }
      button.removeAttribute('aria-busy');
      button.removeAttribute('data-state');
      return;
    }

    if (state !== 'loading' && state !== 'success' && state !== 'error') return;
    if (state === 'loading') {
      if (button.tagName === 'BUTTON' && !button.disabled) {
        button.disabled = true;
        button.dataset.fxBtnTempDisabled = 'true';
      }
      button.setAttribute('aria-busy', 'true');
    } else {
      button.removeAttribute('aria-busy');
    }
    button.setAttribute('data-state', state);
  }

  async function runButtonStateFlow(button, resultState, loadingMs = 1400, doneMs = 1400) {
    if (!(button instanceof HTMLElement)) return;
    if (button.dataset.state) return;

    setButtonState(button, 'loading');
    await new Promise((resolve) => setTimeout(resolve, loadingMs));
    setButtonState(button, resultState);
    await new Promise((resolve) => setTimeout(resolve, doneMs));
    setButtonState(button, '');
  }

  function bindButton(button) {
    if (!isElementButtonLike(button)) return;
    if (button.dataset.buttonFxBound === 'true') return;

    button.dataset.buttonFxBound = 'true';
    button.dataset.buttonFx = '';
    button.classList.add('fx-btn');

    ensureStructure(button);

    button.addEventListener('pointerdown', (event) => {
      createRipple(button, event);
    });
  }

  function bindAll(root = document) {
    if (!(root instanceof Document || root instanceof Element)) return;

    if (root instanceof Element && isElementButtonLike(root)) {
      bindButton(root);
    }

    root.querySelectorAll(`${AUTO_BUTTON_SELECTOR}, ${OPT_IN_SELECTOR}`).forEach(bindButton);
  }

  bindAll();

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof HTMLElement)) return;
        bindAll(node);
      });
    }
  });

  observer.observe(document.documentElement, {
    childList: true,
    subtree: true
  });

  window.ButtonFx = Object.freeze({
    bindAll,
    setState: setButtonState,
    clearState: (button) => setButtonState(button, ''),
    runFlow: runButtonStateFlow
  });
})();
