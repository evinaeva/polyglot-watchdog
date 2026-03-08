const PAGE_SIZE = 20;
let allRows = [];
let filteredRows = [];
let currentPage = 1;
let currentScale = 1;

const domainDropdown = document.getElementById('domainDropdown');
const collectPullsButton = document.getElementById('collectPullsButton');
const pullRows = document.getElementById('pullRows');
const pageLabel = document.getElementById('pageLabel');
const prevPage = document.getElementById('prevPage');
const nextPage = document.getElementById('nextPage');

const urlFilter = document.getElementById('urlFilter');
const elementTypeFilter = document.getElementById('elementTypeFilter');
const imagesFilter = document.getElementById('imagesFilter');
const buttonsFilter = document.getElementById('buttonsFilter');
const inputsFilter = document.getElementById('inputsFilter');

const screenshotModal = document.getElementById('screenshotModal');
const modalImage = document.getElementById('modalImage');
const modalOverlay = document.querySelector('.modal-overlay');

function uniqueSorted(values) {
  return [...new Set(values)].sort((a, b) => a.localeCompare(b));
}

function populateFilterOptions() {
  const types = uniqueSorted(allRows.map((row) => row.element_type));
  elementTypeFilter.innerHTML = '<option value="">All</option>';
  for (const type of types) {
    const option = document.createElement('option');
    option.value = type;
    option.textContent = type;
    elementTypeFilter.appendChild(option);
  }
}

function applyFilters() {
  const selectedUrlText = urlFilter.value.trim().toLowerCase();
  const selectedType = elementTypeFilter.value;

  filteredRows = allRows.filter((row) => {
    if (selectedUrlText && !row.url.toLowerCase().includes(selectedUrlText)) return false;
    if (selectedType && row.element_type !== selectedType) return false;

    const hasTypeCheckbox = imagesFilter.checked || buttonsFilter.checked || inputsFilter.checked;
    if (hasTypeCheckbox) {
      const imageMatch = imagesFilter.checked && row.element_type === 'img';
      const buttonMatch = buttonsFilter.checked && row.element_type === 'button';
      const inputMatch = inputsFilter.checked && row.element_type === 'input';
      if (!(imageMatch || buttonMatch || inputMatch)) return false;
    }

    return true;
  });

  currentPage = 1;
  renderRows();
}

function renderRows() {
  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  currentPage = Math.min(currentPage, totalPages);
  const start = (currentPage - 1) * PAGE_SIZE;
  const rows = filteredRows.slice(start, start + PAGE_SIZE);

  pullRows.innerHTML = '';
  for (const row of rows) {
    const tr = document.createElement('tr');
    const decision = row.decision || '';
    tr.innerHTML = `
      <td>${row.url}</td>
      <td>${row.element_type}</td>
      <td>${row.text}</td>
      <td><img class="thumb" src="${row.screenshot_thumbnail}" alt="thumbnail" data-full="${row.screenshot_full}" title="Open full screenshot preview." /></td>
      <td>
        <select data-item-id="${row.item_id}" class="decision-select" title="Choose how this element should be treated in dataset building.">
          <option value="" ${decision === '' ? 'selected' : ''}>--</option>
          <option value="IGNORE_ENTIRE_ELEMENT" ${decision === 'IGNORE_ENTIRE_ELEMENT' ? 'selected' : ''} title="Exclude this element from comparison.">IGNORE_ENTIRE_ELEMENT</option>
          <option value="MASK_VARIABLE" ${decision === 'MASK_VARIABLE' ? 'selected' : ''} title="Keep element but mask changing values.">MASK_VARIABLE</option>
          <option value="ALWAYS_COLLECT" ${decision === 'ALWAYS_COLLECT' ? 'selected' : ''} title="Always keep this element in collection output.">ALWAYS_COLLECT</option>
        </select>
      </td>`;
    pullRows.appendChild(tr);
  }

  pageLabel.textContent = `Page ${currentPage} / ${totalPages}`;
  bindRowInteractions();
}

function bindRowInteractions() {
  document.querySelectorAll('.thumb').forEach((thumb) => {
    thumb.addEventListener('click', () => {
      currentScale = 1;
      modalImage.style.transform = `translateY(-50%) scale(${currentScale})`;
      modalImage.src = thumb.dataset.full;
      screenshotModal.classList.remove('hidden');
    });
  });

  document.querySelectorAll('.decision-select').forEach((select) => {
    select.addEventListener('change', async (event) => {
      const itemId = event.target.getAttribute('data-item-id');
      const ruleType = event.target.value;
      if (!ruleType) return;
      await fetch('/api/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId, rule_type: ruleType }),
      });
      const row = allRows.find((entry) => entry.item_id === itemId);
      if (row) row.decision = ruleType;
    });
  });
}

async function loadDomains() {
  const response = await fetch('/api/domains');
  const payload = await response.json();
  domainDropdown.innerHTML = '';
  for (const domain of payload.items || []) {
    const option = document.createElement('option');
    option.value = domain;
    option.textContent = domain;
    domainDropdown.appendChild(option);
  }
}

async function loadPullRows() {
  const response = await fetch('/api/pulls');
  const payload = await response.json();
  allRows = (payload.rows || []).sort((a, b) => a.item_id.localeCompare(b.item_id));
  populateFilterOptions();
  applyFilters();
}

collectPullsButton.addEventListener('click', loadPullRows);
prevPage.addEventListener('click', () => {
  currentPage = Math.max(1, currentPage - 1);
  renderRows();
});
nextPage.addEventListener('click', () => {
  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  currentPage = Math.min(totalPages, currentPage + 1);
  renderRows();
});

[urlFilter, elementTypeFilter, imagesFilter, buttonsFilter, inputsFilter].forEach((input) => {
  input.addEventListener('input', applyFilters);
  input.addEventListener('change', applyFilters);
});

modalOverlay.addEventListener('click', () => screenshotModal.classList.add('hidden'));
screenshotModal.addEventListener('wheel', (event) => {
  event.preventDefault();
  currentScale += event.deltaY < 0 ? 0.1 : -0.1;
  currentScale = Math.max(0.2, Math.min(3, currentScale));
  modalImage.style.transform = `translateY(-50%) scale(${currentScale})`;
});

loadDomains();
renderRows();
