document.addEventListener("DOMContentLoaded", () => {
  const open = (id) => {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-visible");
    const focusable = modal.querySelector("input");
    if (focusable) setTimeout(() => focusable.focus(), 80);
  };
  const close = (modal) => {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    if (!document.querySelector(".modal-backdrop.is-open"))
      document.body.classList.remove("modal-visible");
  };
  document
    .querySelectorAll("[data-open-modal]")
    .forEach((btn) =>
      btn.addEventListener("click", () => open(btn.dataset.openModal)),
    );
  document
    .querySelectorAll("[data-close-modal]")
    .forEach((btn) =>
      btn.addEventListener("click", () =>
        close(btn.closest(".modal-backdrop")),
      ),
    );
  document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) close(backdrop);
    });
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape")
      document.querySelectorAll(".modal-backdrop.is-open").forEach(close);
  });
  document.querySelectorAll("[data-edit-product]").forEach((btn) =>
    btn.addEventListener("click", () => {
      const form = document.getElementById("editProductForm");
      form.action = `/products/${btn.dataset.id}/edit`;
      [
        "product_name",
        "category",
        "supplier",
        "unit_price",
        "quantity_in_stock",
        "reorder_level",
      ].forEach((name, i) => {
        form.elements[name].value = [
          btn.dataset.name,
          btn.dataset.category,
          btn.dataset.supplier,
          btn.dataset.price,
          btn.dataset.quantity,
          btn.dataset.reorder,
        ][i];
      });
      open("editModal");
    }),
  );
  document.querySelectorAll("[data-delete-product]").forEach((btn) =>
    btn.addEventListener("click", () => {
      document.getElementById("deleteProductName").textContent =
        btn.dataset.name;
      document.getElementById("deleteProductForm").action =
        `/products/${btn.dataset.id}/delete`;
      open("deleteModal");
    }),
  );
});
