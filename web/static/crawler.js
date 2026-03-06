const collectButton = document.getElementById('collectUrlsButton');
const domainInput = document.getElementById('domainInput');
const inventoryBody = document.getElementById('urlInventoryBody');

collectButton.addEventListener('click', async () => {
  const domain = domainInput.value.trim();
  const response = await fetch(`/api/url-inventory?domain=${encodeURIComponent(domain)}`);
  const payload = await response.json();
  inventoryBody.innerHTML = '';
  for (const url of payload.urls || []) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${url}</td>`;
    inventoryBody.appendChild(tr);
  }
});
