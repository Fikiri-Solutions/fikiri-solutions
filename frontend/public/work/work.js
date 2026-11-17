(function () {
  const data = window.FIKIRI_LOOKBOOK;
  if (!data) return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function el(tag, className) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    return node;
  }

  function logoPlate(item) {
    const plate = el("div", item.darkLogoPlate ? "logo-plate dark" : "logo-plate");
    if (item.logoTall) {
      plate.classList.add("tall");
    }
    if (item.logoSrc) {
      const img = el("img");
      img.src = item.logoSrc;
      img.alt = item.logoAlt || "";
      img.loading = "lazy";
      img.decoding = "async";
      img.onerror = function () {
        plate.replaceChildren();
        const mark = el("span", "logo-fallback");
        mark.textContent = item.fallbackMark || "?";
        plate.appendChild(mark);
      };
      plate.appendChild(img);
    } else {
      const mark = el("span", "logo-fallback");
      mark.textContent = item.fallbackMark || "?";
      plate.appendChild(mark);
    }
    return plate;
  }

  function projectCard(item) {
    const article = el("article", "project");
    article.appendChild(logoPlate(item));

    const title = el("h3");
    title.textContent = item.name;
    article.appendChild(title);

    const category = el("p", "category");
    category.textContent = item.category;
    article.appendChild(category);

    const summary = el("p", "summary");
    summary.textContent = item.summary;
    article.appendChild(summary);

    const link = el("a", "btn ghost open");
    link.href = item.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Open site";
    link.setAttribute("aria-label", `Open ${item.name} website`);
    article.appendChild(link);

    return article;
  }

  function previewCard(item) {
    const li = el("li", "preview-item");

    const thumbLink = el("a", "preview-thumb");
    thumbLink.href = item.url;
    thumbLink.target = "_blank";
    thumbLink.rel = "noopener noreferrer";
    thumbLink.setAttribute("aria-label", `Open preview: ${item.name}`);

    if (item.thumbSrc) {
      const img = el("img");
      img.src = item.thumbSrc;
      img.alt = item.thumbAlt || "";
      img.loading = "lazy";
      img.decoding = "async";
      img.onerror = function () {
        thumbLink.classList.add("is-missing");
        img.remove();
      };
      thumbLink.appendChild(img);
    }

    const body = el("div", "preview-body");

    const title = el("h3");
    title.textContent = item.name;
    body.appendChild(title);

    const category = el("p", "category");
    category.textContent = item.category;
    body.appendChild(category);

    const summary = el("p", "summary");
    summary.textContent = item.summary;
    body.appendChild(summary);

    const link = el("a", "btn ghost open");
    link.href = item.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Open preview";
    link.setAttribute("aria-label", `Open preview: ${item.name}`);
    body.appendChild(link);

    li.appendChild(thumbLink);
    li.appendChild(body);
    return li;
  }

  function mountLive() {
    const rail = document.getElementById("live-rail");
    if (!rail) return;
    const frag = document.createDocumentFragment();
    data.live.forEach(function (item) {
      frag.appendChild(projectCard(item));
    });
    rail.appendChild(frag);
  }

  function mountMockups() {
    const list = document.getElementById("mockups-list");
    if (!list) return;
    const frag = document.createDocumentFragment();
    data.mockups.forEach(function (item) {
      frag.appendChild(previewCard(item));
    });
    list.appendChild(frag);
  }

  function observeIn() {
    const targets = document.querySelectorAll(".project, .preview-item");
    if (!targets.length) return;
    if (reduceMotion || !("IntersectionObserver" in window)) {
      targets.forEach(function (node) {
        node.classList.add("is-in");
      });
      return;
    }
    const io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
    );
    targets.forEach(function (node) {
      io.observe(node);
    });
  }

  function wireRailControls() {
    document.querySelectorAll(".rail-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const id = btn.getAttribute("data-rail") === "live" ? "live-rail" : null;
        const rail = id ? document.getElementById(id) : null;
        if (!rail) return;
        const dir = Number(btn.getAttribute("data-dir") || "1");
        const step = Math.max(rail.clientWidth * 0.78, 280);
        rail.scrollBy({ left: dir * step, behavior: reduceMotion ? "auto" : "smooth" });
      });
    });
  }

  mountLive();
  mountMockups();
  wireRailControls();
  observeIn();
})();
