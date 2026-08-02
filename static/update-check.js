async function checkForUpdate() {
  try {
    const res = await fetch("/api/check-update", {
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

document.addEventListener(
  "DOMContentLoaded",
  checkForUpdate
);