const domainInput = document.getElementById("domainInput");
const loadButton = document.getElementById("loadButton");
const replaceButton = document.getElementById("replaceButton");
const addButton = document.getElementById("addButton");
const clearButton = document.getElementById("clearButton");
const urlsMultiline = document.getElementById("urlsMultiline");
const updatedAt = document.getElementById("updatedAt");
const savedUrlsBody = document.getElementById("savedUrlsBody");
const errorBox = document.getElementById("errorBox");

function setError(message) {
  if (!message) {
    errorBox.textContent = "";
    errorBox.classList.add("hidden");
    return;
  }
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function render(data) {
  const urls = Array.isArray(data.urls) ? data.urls : [];
  updatedAt.textContent = data.updated_at || "-";
  urlsMultiline.value = urls.join("\n");
  savedUrlsBody.innerHTML = "";

  for (const url of urls) {
    const tr = document.createElement("tr");

    const urlCell = document.createElement("td");
    urlCell.textContent = url;

    const actionCell = document.createElement("td");
    const deleteButton = document.createElement("button");
    deleteButton.textContent = "Delete";
    deleteButton.title = "Delete this URL from the saved seed list.";
    deleteButton.addEventListener("click", async () => {
      await mutate("/api/seed-urls/delete", { domain: domainInput.value, url });
    });
    actionCell.appendChild(deleteButton);

    tr.appendChild(urlCell);
    tr.appendChild(actionCell);
    savedUrlsBody.appendChild(tr);
  }
}

async function callApi(path, method, payload) {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `request failed (${response.status})`);
  }
  return data;
}

async function load() {
  setError("");
  try {
    const params = new URLSearchParams({ domain: domainInput.value });
    const response = await fetch(`/api/seed-urls?${params.toString()}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || `request failed (${response.status})`);
    }
    render(data);
  } catch (error) {
    setError(error.message || "Failed to load seed URLs");
  }
}

async function mutate(path, payload) {
  setError("");
  try {
    const method = path === "/api/seed-urls" ? "PUT" : "POST";
    const data = await callApi(path, method, payload);
    render(data);
  } catch (error) {
    setError(error.message || "Request failed");
  }
}

loadButton.addEventListener("click", load);
replaceButton.addEventListener("click", () => mutate("/api/seed-urls", {
  domain: domainInput.value,
  urls_multiline: urlsMultiline.value,
}));
addButton.addEventListener("click", () => mutate("/api/seed-urls/add", {
  domain: domainInput.value,
  urls_multiline: urlsMultiline.value,
}));
clearButton.addEventListener("click", () => mutate("/api/seed-urls/clear", {
  domain: domainInput.value,
}));

window.addEventListener("DOMContentLoaded", load);
