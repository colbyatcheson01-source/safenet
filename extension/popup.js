// SafeNet Reporter - Popup
const DEFAULT_SERVER = "http://127.0.0.1:5000";

let pendingUrl = "";
let pendingPlatform = "";

function getServerUrl(callback) {
  chrome.storage.sync.get(["serverUrl"], (result) => {
    callback(result.serverUrl || DEFAULT_SERVER);
  });
}

function getApiKey(callback) {
  chrome.storage.sync.get(["apiKey"], (result) => {
    callback(result.apiKey || "");
  });
}

document.addEventListener("DOMContentLoaded", () => {
  chrome.storage.session.get(["pendingReport"], (result) => {
    if (result.pendingReport) {
      pendingUrl = result.pendingReport.url;
      pendingPlatform = result.pendingReport.platform;
      document.getElementById("urlDisplay").textContent = pendingUrl;
      document.getElementById("platform").value = pendingPlatform;
      chrome.storage.session.remove("pendingReport");
    } else {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0]?.url) {
          pendingUrl = tabs[0].url;
          document.getElementById("urlDisplay").textContent = pendingUrl;
          document.getElementById("platform").value = detectPlatform(pendingUrl);
        }
      });
    }
  });

  document.querySelectorAll(".quick-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.getElementById("description").value = `[${btn.dataset.category}] `;
      document.getElementById("description").focus();
    });
  });

  document.getElementById("submitBtn").addEventListener("click", submitReport);
  document.getElementById("optionsBtn").addEventListener("click", () => {
    chrome.runtime.openOptionsPage();
  });
  document.getElementById("dashboardLink").addEventListener("click", (e) => {
    e.preventDefault();
    getServerUrl((url) => chrome.tabs.create({ url: `${url}/reports` }));
    window.close();
  });
});

function detectPlatform(url) {
  const u = url.toLowerCase();
  if (u.includes("facebook.com")) return "facebook";
  if (u.includes("twitter.com") || u.includes("x.com")) return "twitter";
  if (u.includes("instagram.com")) return "instagram";
  if (u.includes("tiktok.com")) return "tiktok";
  if (u.includes("snapchat.com")) return "snapchat";
  if (u.includes("youtube.com")) return "youtube";
  if (u.includes("reddit.com")) return "reddit";
  if (u.includes("discord.com")) return "discord";
  if (u.includes("telegram.org") || u.includes("t.me")) return "telegram";
  if (u.includes("whatsapp.com")) return "whatsapp";
  if (u.includes("linkedin.com")) return "linkedin";
  return "other";
}

function submitReport() {
  const btn = document.getElementById("submitBtn");
  const statusEl = document.getElementById("status");
  btn.disabled = true;
  btn.textContent = "Submitting...";
  statusEl.style.display = "none";

  const data = {
    platform: document.getElementById("platform").value,
    profile_url: pendingUrl,
    description: document.getElementById("description").value || "Reported via SafeNet Chrome extension",
    severity: document.getElementById("severity").value,
    category: "other",
    email: document.getElementById("email").value || "",
  };

  getServerUrl((serverUrl) => {
    getApiKey((apiKey) => {
      const headers = { "Content-Type": "application/json" };
      if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

      fetch(`${serverUrl}/api/report`, {
        method: "POST",
        headers,
        body: JSON.stringify(data),
      })
        .then((r) => r.json())
        .then((result) => {
          statusEl.className = "status success";
          statusEl.textContent = result.message || "Report submitted!";
          statusEl.style.display = "block";
          btn.textContent = "✓ Submitted";
          chrome.notifications.create("safenet-report", {
            type: "basic",
            iconUrl: "icons/icon48.png",
            title: "SafeNet Report Submitted",
            message: `Report for ${data.platform} has been recorded.`,
          });
        })
        .catch((err) => {
          statusEl.className = "status error";
          statusEl.textContent = "Failed to submit. Check your SafeNet server is running.";
          statusEl.style.display = "block";
          btn.disabled = false;
          btn.textContent = "Submit Report";
        });
    });
  });
}
