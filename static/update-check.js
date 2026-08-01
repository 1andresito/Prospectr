async function checkForUpdate() {
    try {
      const res = await fetch("/api/check-update");
      const data = await res.json();
  
      const badge = document.getElementById("version-badge");
      if (badge) {
        badge.textContent = `v${data.current_version}`;
        badge.classList.remove("badge-unreleased", "badge-update-available");
  
        if (data.status === "unreleased") {
          badge.textContent += " (unreleased)";
          badge.classList.add("badge-unreleased");
        } else if (data.status === "update_available") {
          badge.classList.add("badge-update-available");
        }
      }
  
      if (data.status === "update_available") {
        document.getElementById("update-link").href = data.release_url;
        document.getElementById("update-banner").style.display = "block";
      } else if (data.status === "unreleased") {
        console.log(`Running unreleased version ${data.current_version} (latest published: ${data.latest_version})`);
      }
    } catch (e) {
      console.error("Failed to check for update:", e);
    }
  }
  document.addEventListener("DOMContentLoaded", checkForUpdate);