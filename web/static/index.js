const domainInput = document.getElementById("domainInput");
const runIdInput = document.getElementById("runIdInput");
const applyBtn = document.getElementById('applyIssueQuery');
const queryInput = document.getElementById('issueQuery');
const table = document.getElementById('issuesTable');
const tbody = table.querySelector('tbody');

applyBtn.addEventListener('click', async () => {
  const query = queryInput.value.trim();
  const params = new URLSearchParams({ domain: domainInput.value.trim(), run_id: runIdInput.value.trim(), q: query });
  const endpoint = `/api/issues?${params.toString()}`;
  const response = await fetch(endpoint);
  const payload = await response.json();
  const issues = payload.issues || [];

  tbody.innerHTML = '';
  for (const issue of issues) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${issue.id}</td><td>${issue.category}</td><td>${issue.url}</td><td>${issue.message}</td>`;
    tbody.appendChild(tr);
  }

  table.classList.remove('hidden');
});
