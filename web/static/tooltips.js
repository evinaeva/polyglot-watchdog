function applyTooltips() {
  const tooltipMap = {
    issueQuery: 'tooltip.issueQuery',
    applyIssueQuery: 'tooltip.applyIssueQuery',
    domainInput: 'tooltip.domainInput',
    loadButton: 'tooltip.loadButton',
    replaceButton: 'tooltip.replaceButton',
    addButton: 'tooltip.addButton',
    clearButton: 'tooltip.clearButton',
    urlsMultiline: 'tooltip.urlsMultiline',
    collectUrlsButton: 'tooltip.collectUrlsButton',
    languageSubdomain: 'tooltip.languageSubdomain',
    domainDropdown: 'tooltip.domainDropdown',
    collectPullsButton: 'tooltip.collectPullsButton',
    urlFilter: 'tooltip.urlFilter',
    elementTypeFilter: 'tooltip.elementTypeFilter',
    imagesFilter: 'tooltip.imagesFilter',
    buttonsFilter: 'tooltip.buttonsFilter',
    inputsFilter: 'tooltip.inputsFilter',
    prevPage: 'tooltip.prevPage',
    nextPage: 'tooltip.nextPage',
  };

  Object.entries(tooltipMap).forEach(([id, key]) => {
    const element = document.getElementById(id);
    if (element) {
      element.title = i18n.t(key);
    }
  });
}

window.addEventListener('DOMContentLoaded', applyTooltips);
document.addEventListener('pw:i18n:ready', applyTooltips);
document.addEventListener('pw:i18n:changed', applyTooltips);
