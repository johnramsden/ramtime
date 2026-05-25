// Display a live clock in the #live-clock element (if present).
(function () {
  const el = document.getElementById("live-clock");
  if (!el) return;

  function update() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    el.textContent =
      now.getFullYear() +
      "-" +
      pad(now.getMonth() + 1) +
      "-" +
      pad(now.getDate()) +
      " " +
      pad(now.getHours()) +
      ":" +
      pad(now.getMinutes()) +
      ":" +
      pad(now.getSeconds());
  }

  update();
  setInterval(update, 1000);
})();
