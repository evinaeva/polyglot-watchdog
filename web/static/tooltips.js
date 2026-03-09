function applyTooltips() {
  const tooltipMap = {
    issueQuery: 'Enter a URL fragment or keyword, then apply query to load issues.',
    applyIssueQuery: 'Fetch issues using the current query. The table stays empty until you run a query.',

    domainInput: 'Domain used for the current page action.',
    loadButton: 'Load saved seed URLs for this domain.',
    replaceButton: 'Replace saved seed URLs with the textarea content.',
    addButton: 'Add textarea URLs to existing saved URLs (deduplicated).',
    clearButton: 'Clear all saved seed URLs for this domain.',
    urlsMultiline: 'Enter one URL per line.',

    collectUrlsButton: 'Load URL inventory for the selected domain (current page wiring is mock-backed).',

    languageSubdomain: 'Language/domain hint used while inspecting pulling rows.',
    domainDropdown: 'Pick a domain for pull-row inspection.',
    collectPullsButton: 'Load pull rows (currently mock-backed in this UI).',
    urlFilter: 'Filter rows by URL text.',
    elementTypeFilter: 'Filter rows by element type.',
    imagesFilter: 'Show only image rows when checked.',
    buttonsFilter: 'Show only button rows when checked.',
    inputsFilter: 'Show only input rows when checked.',
    prevPage: 'Go to previous page of filtered rows.',
    nextPage: 'Go to next page of filtered rows.',
  };

  Object.entries(tooltipMap).forEach(([id, text]) => {
    const element = document.getElementById(id);
    if (element) {
      element.title = text;
    }
  });
}

window.addEventListener('DOMContentLoaded', applyTooltips);
