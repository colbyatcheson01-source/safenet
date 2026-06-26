// SafeNet Reporter - Background Service Worker
const DEFAULT_SERVER = "http://127.0.0.1:5000";

function getServerUrl() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(["serverUrl"], (result) => {
      resolve(result.serverUrl || DEFAULT_SERVER);
    });
  });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "report-profile",
    title: "Report this profile to SafeNet",
    contexts: ["link"],
  });
  chrome.contextMenus.create({
    id: "report-page",
    title: "Report this page to SafeNet",
    contexts: ["page"],
  });
  chrome.contextMenus.create({
    id: "separator",
    type: "separator",
    contexts: ["link", "page", "selection"],
  });
  chrome.contextMenus.create({
    id: "open-safenet",
    title: "Open SafeNet Dashboard",
    contexts: ["action"],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "open-safenet") {
    getServerUrl().then((url) => chrome.tabs.create({ url }));
    return;
  }
  const url = info.linkUrl || info.pageUrl || tab?.url || "";
  const platform = detectPlatform(url);
  chrome.storage.session.set(
    { pendingReport: { url, platform, source: info.menuItemId } },
    () => {
      chrome.action.openPopup();
    }
  );
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
  if (u.includes("pinterest.com")) return "pinterest";
  if (u.includes("tumblr.com")) return "tumblr";
  if (u.includes("twitch.tv")) return "twitch";
  if (u.includes("onlyfans.com")) return "onlyfans";
  return "other";
}

chrome.notifications.onClicked.addListener((id) => {
  if (id.startsWith("safenet-")) {
    getServerUrl().then((url) => chrome.tabs.create({ url: `${url}/reports` }));
  }
});
