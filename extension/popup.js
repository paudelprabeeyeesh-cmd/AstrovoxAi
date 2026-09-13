chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
  document.getElementById("summarize").addEventListener("click", async () => {
    const [tab] = await chrome.tabs.sendMessage(tabs[0].id, {action: "getText"});
    const res = await fetch("https://api.astrovox.ai/v1/solve", {
      method: "POST",
      headers: { "Authorization": `Bearer ${localStorage.getItem("api_key") || ""}`, "Content-Type": "application/json" },
      body: JSON.stringify({ text: `Summarize: ${tab.text}` })
    });
    const data = await res.json();
    document.getElementById("result").value = data.result;
  });
});
