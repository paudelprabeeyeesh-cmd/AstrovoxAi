chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "getText") {
    sendResponse({ text: document.body.innerText });
  }
});
