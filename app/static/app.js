const textarea = document.getElementById("scenario");
const runButton = document.getElementById("run-btn");
const output = document.getElementById("output");
const cidDisplay = document.getElementById("cid-display");
const cidStatus = document.getElementById("cid-status");
const modeIndicator = document.getElementById("mode-indicator");
const modeWarning = document.getElementById("mode-warning");

function setOutput(content, isError = false) {
  output.innerHTML = "";
  const pre = document.createElement("pre");
  pre.textContent = content;
  if (isError) {
    pre.style.color = "#ff8a8a";
  }
  output.appendChild(pre);
}

function updateStorageInfo(record) {
  if (record && record.storage && record.storage.cid) {
    cidDisplay.textContent = record.storage.cid;
    cidStatus.textContent = "Stored on Pinata/IPFS";
  } else if (record) {
    cidDisplay.textContent = "CID not available";
    cidStatus.textContent = "Storage not available (token missing or upload failed).";
  } else {
    cidDisplay.textContent = "CID not available";
    cidStatus.textContent = "Storage status unknown.";
  }
}

function updateModeInfo(label, fallback) {
  const text = label ? `Mode: ${label}` : "Mode: UNKNOWN";
  modeIndicator.textContent = text;
  if (fallback) {
    modeWarning.hidden = false;
    modeWarning.textContent = "LLM fallback to deterministic Sentinel engine.";
  } else {
    modeWarning.hidden = true;
  }
}

updateModeInfo("PENDING", false);

runButton.addEventListener("click", async () => {
  const scenario = textarea.value.trim();
  if (!scenario) {
    setOutput("Please describe a scenario before running Sentinel.", true);
    updateStorageInfo(null);
    return;
  }

  runButton.disabled = true;
  setOutput("Running Sentinel governance pass…");
  updateStorageInfo(null);
  updateModeInfo("PROCESSING", false);

  try {
    const response = await fetch("/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario }),
    });

    const modeLabel = response.headers.get("x-sentinel-mode") || "UNKNOWN";
    const fallbackFlag = response.headers.get("x-sentinel-fallback") === "1";
    updateModeInfo(modeLabel, fallbackFlag);

    if (!response.ok) {
      throw new Error(`Server responded with ${response.status}`);
    }

    const data = await response.json();
    setOutput(JSON.stringify(data, null, 2));
    updateStorageInfo(data);
  } catch (error) {
    setOutput(`Sentinel failed: ${error.message}`, true);
  } finally {
    runButton.disabled = false;
  }
});
