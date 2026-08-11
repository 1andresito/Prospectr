let latestReleaseUrl = null;

async function checkForUpdate() {
  try {
    const res = await apiFetch("/api/check-update", {
      cache: "no-store"
    });

    if (!res.ok) {
      throw new Error(`Update check failed with HTTP ${res.status}`);
    }

    const data = await res.json();

    const badge = document.getElementById("version-badge");
    const banner = document.getElementById("update-banner");
    const link = document.getElementById("update-link");

    if (badge) {
      badge.textContent = `v${data.current_version}`;

      badge.classList.remove(
        "badge-unreleased",
        "badge-update-available"
      );

      if (data.status === "unreleased") {
        badge.textContent += " (unreleased)";
        badge.classList.add("badge-unreleased");
      } else if (data.status === "update_available") {
        badge.classList.add("badge-update-available");
      }
    }

    if (data.status === "update_available") {
      latestReleaseUrl = data.release_url;

      if (link) {
        link.href = data.release_url;
      }

      if (banner) {
        banner.style.display = "block";
      }
    } else if (banner) {
      banner.style.display = "none";
    }

    if (data.status === "check_failed") {
      console.warn(
        "Prospectr could not check for updates.",
        data.diagnostic || data
      );

      return;
    }

    console.log(
      "Prospectr update check:",
      data.diagnostic || data
    );

  } catch (error) {
    console.error(
      "Failed to check for update:",
      error
    );
  }
}

function showUpdateDialog() {
  const overlay = document.getElementById("update-overlay");
  const message = document.getElementById("update-dialog-message");
  const progressTrack = document.getElementById("update-progress-track");
  const confirmBtn = document.getElementById("update-confirm-btn");
  const cancelBtn = document.getElementById("update-cancel-btn");
  const fallback = document.getElementById("update-dialog-fallback");

  message.textContent = "A new version of Prospectr is available. Update now? The app will restart.";
  progressTrack.classList.add("hidden");
  confirmBtn.disabled = false;
  confirmBtn.style.display = "";
  cancelBtn.style.display = "";
  fallback.classList.add("hidden");

  overlay.classList.remove("hidden");
}

function hideUpdateDialog() {
  document.getElementById("update-overlay").classList.add("hidden");
}

function setUpdateProgress(percent, message) {
  const progressTrack = document.getElementById("update-progress-track");
  const progressBar = document.getElementById("update-progress-bar");
  const messageEl = document.getElementById("update-dialog-message");

  progressTrack.classList.remove("hidden");
  progressBar.style.width = `${percent}%`;
  messageEl.textContent = message;
}

function showUpdateError(message) {
  const messageEl = document.getElementById("update-dialog-message");
  const confirmBtn = document.getElementById("update-confirm-btn");
  const cancelBtn = document.getElementById("update-cancel-btn");
  const fallback = document.getElementById("update-dialog-fallback");
  const fallbackLink = document.getElementById("update-fallback-link");

  messageEl.textContent = message;
  confirmBtn.style.display = "none";
  cancelBtn.textContent = "Close";
  cancelBtn.style.display = "";

  if (latestReleaseUrl) {
    fallbackLink.href = latestReleaseUrl;
    fallback.classList.remove("hidden");
  }
}

async function pollUpdateStatus() {
  while (true) {
    let data;
    try {
      const res = await apiFetch("/api/update-status", { cache: "no-store" });
      if (!res.ok) {
        // The old process may already be gone (connection refused) or the
        // new one may be up with a fresh per-launch token (403) — either
        // way, the only way forward is to wait for the server to settle.
        setUpdateProgress(100, "Restarting Prospectr…");
        await waitForServerRestart();
        return;
      }
      data = await res.json();
    } catch (error) {
      setUpdateProgress(100, "Restarting Prospectr…");
      await waitForServerRestart();
      return;
    }

    if (data.stage === "downloading") {
      setUpdateProgress(data.percent, data.message || "Downloading update…");
    } else if (data.stage === "preparing") {
      setUpdateProgress(100, data.message || "Preparing update…");
    } else if (data.stage === "restarting") {
      setUpdateProgress(100, data.message || "Restarting Prospectr…");
      await waitForServerRestart();
      return;
    } else if (data.stage === "error") {
      showUpdateError(data.message || "Update failed.");
      return;
    }

    await sleep(750);
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServerRestart() {
  const maxAttempts = 60;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await sleep(1000);
    try {
      const res = await fetch("/", { cache: "no-store" });
      if (res.ok) {
        window.location.reload();
        return;
      }
    } catch (error) {
      // Still restarting — keep polling.
    }
  }

  showUpdateError(
    "Prospectr is taking longer than expected to restart. Please reopen it manually."
  );
}

async function startUpdate() {
  const confirmBtn = document.getElementById("update-confirm-btn");
  const cancelBtn = document.getElementById("update-cancel-btn");

  confirmBtn.disabled = true;
  cancelBtn.style.display = "none";
  setUpdateProgress(0, "Starting update…");

  try {
    const res = await apiFetch("/api/apply-update", { method: "POST" });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      showUpdateError(data.error || "Couldn't start the update.");
      return;
    }

    await pollUpdateStatus();
  } catch (error) {
    showUpdateError("Couldn't start the update.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  checkForUpdate();

  const updateNowBtn = document.getElementById("update-now-btn");
  const confirmBtn = document.getElementById("update-confirm-btn");
  const cancelBtn = document.getElementById("update-cancel-btn");
  const closeBtn = document.getElementById("update-close-btn");

  updateNowBtn?.addEventListener("click", showUpdateDialog);
  confirmBtn?.addEventListener("click", startUpdate);
  cancelBtn?.addEventListener("click", hideUpdateDialog);
  closeBtn?.addEventListener("click", hideUpdateDialog);
});
