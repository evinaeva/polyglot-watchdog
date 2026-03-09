(() => {
  const pathname = window.location.pathname;
  const allowedPaths = new Set(["/", "/crawler", "/pulling", "/urls", "/about", "/testbench"]);
  const activePath = allowedPaths.has(pathname) ? pathname : null;
  if (!activePath) return;

  const links = document.querySelectorAll('nav a[href]');
  links.forEach((link) => {
    const href = link.getAttribute('href');
    const isHome = activePath === "/";
    const isMatch = isHome ? href === "/" : href === activePath;
    if (isMatch) {
      link.classList.add('active');
      link.setAttribute('aria-current', 'page');
    }
  });
})();
