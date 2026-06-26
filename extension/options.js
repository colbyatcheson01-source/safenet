// SafeNet Reporter - Options
document.addEventListener("DOMContentLoaded", () => {
  chrome.storage.sync.get(["serverUrl", "apiKey"], (result) => {
    document.getElementById("serverUrl").value = result.serverUrl || "http://127.0.0.1:5000";
    document.getElementById("apiKey").value = result.apiKey || "";
  });
  document.getElementById("saveBtn").addEventListener("click", saveSettings);
  document.getElementById("testBtn").addEventListener("click", testConnection);
});

function saveSettings() {
  const serverUrl = document.getElementById("serverUrl").value.trim();
  const apiKey = document.getElementById("apiKey").value.trim();
  const statusEl = document.getElementById("status");

  chrome.storage.sync.set({ serverUrl, apiKey }, () => {
    statusEl.className = "status success";
    statusEl.textContent = "Settings saved!";
    statusEl.style.display = "block";
    setTimeout(() => { statusEl.style.display = "none"; }, 2000);
  });
}

function testConnection() {
  const serverUrl = document.getElementById("serverUrl").value.trim();
  const apiKey = document.getElementById("apiKey").value.trim();
  const resultEl = document.getElementById("testResult");

  resultEl.textContent = "Testing...";
  resultEl.className = "test-result";

  const headers = {};
  if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

  fetch(`${serverUrl}/api/update/status`, { headers })
    .then((r) => r.json())
    .then((data) => {
      resultEl.className = "test-result ok";
      resultEl.textContent = `✓ Connected! SafeNet v${data.current_version || "unknown"}`;
    })
    .catch((err) => {
      resultEl.className = "test-result fail";
      resultEl.textContent = "✗ Connection failed. Make sure SafeNet is running at that URL.";
    });
}
