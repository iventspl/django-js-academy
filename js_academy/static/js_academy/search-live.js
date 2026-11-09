/* Instant, keyboard-friendly results for the JS search page. */
(() => {
  const form = document.querySelector("[data-js-search]");
  if (!form) return;
  const input = form.querySelector('input[name="q"]');
  const results = document.getElementById("js-search-results");
  const empty = document.getElementById("js-search-empty");
  const count = document.getElementById("js-search-count");
  const status = document.getElementById("js-search-status");
  if (!input || !results) return;

  let timer = null;
  let controller = null;
  let activeIndex = -1;

  const resultLinks = () => [...results.querySelectorAll(".js-search-result")];

  const setActive = (index) => {
    const links = resultLinks();
    links.forEach((link) => link.classList.remove("is-keyboard-active"));
    if (!links.length) {
      activeIndex = -1;
      return;
    }
    activeIndex = (index + links.length) % links.length;
    links[activeIndex].classList.add("is-keyboard-active");
    links[activeIndex].focus({ preventScroll: false });
  };

  const updateStatus = (query, total) => {
    if (count) count.textContent = String(total);
    if (!status) return;
    status.textContent =
      total === 0
        ? `Brak wyników dla „${query}”.`
        : `Dla „${query}” znaleziono ${total} ${total === 1 ? "wynik" : "wyników"}.`;
  };

  const render = (data) => {
    results.replaceChildren();
    const links = data.results.map((item) => {
      const link = document.createElement("a");
      link.className = "js-search-result";
      link.href = item.url;

      const kind = document.createElement("span");
      kind.className = "js-search-kind";
      kind.textContent = item.kind_label;

      const body = document.createElement("span");
      body.className = "js-search-result-body";
      const title = document.createElement("strong");
      title.textContent = item.title;
      body.append(title);
      if (item.meta) {
        const meta = document.createElement("span");
        meta.className = "js-search-meta";
        meta.textContent = item.meta;
        body.append(meta);
      }
      const snippet = document.createElement("span");
      snippet.className = "js-search-snippet";
      snippet.textContent = item.snippet || "";
      body.append(snippet);

      const arrow = document.createElement("span");
      arrow.className = "js-search-arrow";
      arrow.setAttribute("aria-hidden", "true");
      arrow.textContent = "→";

      link.append(kind, body, arrow);
      return link;
    });
    results.append(...links);
    results.hidden = links.length === 0;
    if (empty) empty.hidden = links.length > 0;
    activeIndex = -1;
    updateStatus(data.query, data.count);
  };

  const query = async () => {
    const value = input.value.trim();
    if (value.length < 2) {
      results.replaceChildren();
      results.hidden = true;
      if (empty) empty.hidden = true;
      if (count) count.textContent = "0";
      if (status) status.textContent = "Wpisz co najmniej dwa znaki.";
      return;
    }
    if (controller) controller.abort();
    controller = new AbortController();
    const params = new URLSearchParams({ q: value });
    for (const name of ["typ", "poziom"]) {
      const hidden = form.querySelector(`input[name="${name}"]`);
      if (hidden && hidden.value) params.set(name, hidden.value);
    }
    try {
      const response = await fetch(`${form.dataset.endpoint}?${params}`, {
        signal: controller.signal,
        headers: { Accept: "application/json" },
      });
      if (!response.ok) return;
      render(await response.json());
    } catch (error) {
      if (error.name !== "AbortError") {
        /* Keep the server-rendered results when the network fails. */
      }
    }
  };

  input.addEventListener("input", () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(query, 180);
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" && resultLinks().length) {
      event.preventDefault();
      setActive(0);
    }
  });

  results.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive(activeIndex + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive(activeIndex - 1);
    } else if (event.key === "Escape") {
      input.focus();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
    const tag = document.activeElement?.tagName;
    if (["INPUT", "TEXTAREA", "SELECT"].includes(tag)) return;
    event.preventDefault();
    input.focus();
    input.select();
  });
})();
