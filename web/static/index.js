const applyBtn = document.getElementById('applyIssueQuery');
const queryInput = document.getElementById('issueQuery');
const table = document.getElementById('issuesTable');
const tbody = table.querySelector('tbody');

applyBtn.addEventListener('click', async () => {
  const query = queryInput.value.trim();
  const endpoint = query ? `/api/issues?q=${encodeURIComponent(query)}` : '/api/issues';
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
