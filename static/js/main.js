document.addEventListener("DOMContentLoaded", () => {
  const label = document.getElementById("todayLabel");
  if (label)
    label.textContent = new Intl.DateTimeFormat("en-UG", {
      weekday: "short",
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(new Date());
  const toggle = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");
  if (toggle && sidebar)
    toggle.addEventListener("click", () =>
      sidebar.classList.toggle("sidebar-open"),
    );
  document.querySelectorAll(".flash").forEach((item) => {
    window.setTimeout(() => item.classList.add("flash-dismissed"), 5000);
  });
});
