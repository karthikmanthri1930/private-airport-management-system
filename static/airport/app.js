document.addEventListener("DOMContentLoaded", () => {
  const menuToggle = document.querySelector(".menu-toggle");
  const sidebar = document.getElementById("sidebar");
  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", () => {
      const open = sidebar.classList.toggle("open");
      menuToggle.setAttribute("aria-expanded", String(open));
    });
  }

  const flightSelect = document.getElementById("id_flight");
  const seatSelect = document.getElementById("id_seat_no");
  if (flightSelect && seatSelect) {
    flightSelect.addEventListener("change", async () => {
      seatSelect.innerHTML = '<option value="">Loading seats…</option>';
      if (!flightSelect.value) {
        seatSelect.innerHTML = '<option value="">Choose a flight first</option>';
        return;
      }
      try {
        const response = await fetch(`/flights/${encodeURIComponent(flightSelect.value)}/seats/`, {headers: {"X-Requested-With": "fetch"}});
        if (!response.ok) throw new Error("Unable to load seats");
        const markup = await response.text();
        seatSelect.innerHTML = markup.trim() || '<option value="">No seats available</option>';
      } catch (_) {
        seatSelect.innerHTML = '<option value="">Could not load seats; refresh the page</option>';
      }
    });
  }
});
