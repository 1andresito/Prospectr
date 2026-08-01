async function checkForUpdate() {
    try {
      const res = await fetch("/api/check-update");
      const data = await res.json();
  
      const badge = document.getElementById("version-badge");
      if (badge) badge.textContent = `v${data.current_version}`;
  
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