(function () {
  function readCookie(name) {
    const prefix = `${name}=`;
    const parts = document.cookie.split(';');
    for (const raw of parts) {
      const item = raw.trim();
      if (item.startsWith(prefix)) {
        return decodeURIComponent(item.slice(prefix.length));
      }
    }
    return '';
  }

  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const method = (init.method || 'GET').toUpperCase();
    const isMutating = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);
    if (isMutating) {
      const csrfToken = readCookie('pw_csrf');
      const headers = new Headers(init.headers || {});
      if (csrfToken && !headers.has('X-CSRF-Token')) {
        headers.set('X-CSRF-Token', csrfToken);
      }
      init.headers = headers;
    }
    return originalFetch(input, init);
  };

  const logoutButton = document.getElementById('logoutButton');
  if (logoutButton) {
    logoutButton.addEventListener('click', async () => {
      const response = await fetch('/logout', { method: 'POST' });
      if (response.redirected) {
        window.location.href = response.url;
        return;
      }
      window.location.href = '/login';
    });
  }
})();
