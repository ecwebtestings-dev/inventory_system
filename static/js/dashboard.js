document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("filterForm");
  if (!form) return;

  const rows = document.getElementById("productRows");
  const count = document.getElementById("recordCount");
  const footnote = document.getElementById("tableFootnote");

  let requestNumber = 0;

  const escapeHtml = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );

  const money = (value) =>
    Number(value).toLocaleString("en-UG", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

  async function refresh() {
    const current = ++requestNumber;

    const params = new URLSearchParams({
      q: document.getElementById("searchInput").value,
      category: document.getElementById("categoryFilter").value,
      supplier: document.getElementById("supplierFilter").value,
      low_stock: document.getElementById("lowFilter").checked ? "1" : "0",
    });

    try {
      const response = await fetch(`/products/search?${params.toString()}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      if (!response.ok) throw new Error("Unable to load products");

      const products = await response.json();

      if (current !== requestNumber) return;

      if (count) {
        count.textContent = `${products.length} records`;
      }

      if (footnote) {
        footnote.textContent = `Showing ${products.length} product records`;
      }

      if (!products.length) {
        rows.innerHTML =
          '<tr><td colspan="8" class="empty-state"><b>No matching products</b><span>Try changing your search or filters.</span></td></tr>';
        return;
      }

      rows.innerHTML = products
        .map((p) => {
          const low = p.quantity_in_stock <= p.reorder_level;

          return `<tr>
          <td><div class="product-name-cell"><span class="product-initial">${escapeHtml(p.product_name.charAt(0).toUpperCase())}</span><div><b>${escapeHtml(p.product_name)}</b>${low ? '<span class="stock-status">Low stock</span>' : ""}</div></div></td>
          <td>${escapeHtml(p.category)}</td><td>${escapeHtml(p.supplier)}</td><td class="align-right">UGX ${money(p.unit_price)}</td><td class="align-right quantity-cell">${p.quantity_in_stock}</td><td class="align-right">${p.reorder_level}</td><td>${escapeHtml(p.date_added)}</td>
          <td><div class="row-actions"><button class="icon-action edit-action" data-edit-product data-id="${p.product_id}" data-name="${escapeHtml(p.product_name)}" data-category="${escapeHtml(p.category)}" data-supplier="${escapeHtml(p.supplier)}" data-price="${p.unit_price}" data-quantity="${p.quantity_in_stock}" data-reorder="${p.reorder_level}">Edit</button><button class="icon-action delete-action" data-delete-product data-id="${p.product_id}" data-name="${escapeHtml(p.product_name)}">Delete</button></div></td>
        </tr>`;
        })
        .join("");

      // Re-bind modal actions after replacing table rows.
      rows.querySelectorAll("[data-edit-product]").forEach((btn) =>
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
          ].forEach(
            (name, i) =>
              (form.elements[name].value = [
                btn.dataset.name,
                btn.dataset.category,
                btn.dataset.supplier,
                btn.dataset.price,
                btn.dataset.quantity,
                btn.dataset.reorder,
              ][i]),
          );

          document.getElementById("editModal").classList.add("is-open");
          document
            .getElementById("editModal")
            .setAttribute("aria-hidden", "false");

          document.body.classList.add("modal-visible");
        }),
      );

      rows.querySelectorAll("[data-delete-product]").forEach((btn) =>
        btn.addEventListener("click", () => {
          document.getElementById("deleteProductName").textContent =
            btn.dataset.name;

          document.getElementById("deleteProductForm").action =
            `/products/${btn.dataset.id}/delete`;

          document.getElementById("deleteModal").classList.add("is-open");

          document
            .getElementById("deleteModal")
            .setAttribute("aria-hidden", "false");

          document.body.classList.add("modal-visible");
        }),
      );
    } catch (error) {
      if (current !== requestNumber) return;

      console.error(error);

      rows.innerHTML =
        '<tr><td colspan="8" class="empty-state">Could not load product records. Refresh the page and try again.</td></tr>';
    }
  }

  let debounce;

  document.getElementById("searchInput").addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(refresh, 250);
  });

  ["categoryFilter", "supplierFilter", "lowFilter"].forEach((id) => {
    document.getElementById(id).addEventListener("change", refresh);
  });

  document.getElementById("clearFilters").addEventListener("click", () => {
    document.getElementById("searchInput").value = "";
    document.getElementById("categoryFilter").value = "";
    document.getElementById("supplierFilter").value = "";
    document.getElementById("lowFilter").checked = false;

    refresh();
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    refresh();
  });
});
