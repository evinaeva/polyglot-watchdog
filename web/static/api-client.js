async function safeReadPayload(response) {
  const contentType = (response.headers.get('content-type') || '').toLowerCase();
  if (contentType.includes('application/json')) {
    try {
      return await response.json();
    } catch (_) {
      return {};
    }
  }
  const text = await response.text();
  return { error: text || `Unexpected response (${response.status})` };
}

window.safeReadPayload = safeReadPayload;
