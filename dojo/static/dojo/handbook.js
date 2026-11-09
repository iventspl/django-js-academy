/* Django Handbook — instant, dependency-free search. */
(function () {
  "use strict";

  const root = document.querySelector("[data-handbook]");
  if (!root) return;

  const form = root.querySelector("[data-hb-form]");
  const input = root.querySelector("[data-hb-input]");
  const results = root.querySelector("[data-hb-results]");
  const endpoint = root.dataset.hbEndpoint;
  const idleTemplate = document.getElementById("hb-idle-template");
  if (!form || !input || !results || !endpoint) return;

  const initialResults = results.innerHTML;
  const idleMarkup = idleTemplate ? idleTemplate.innerHTML : initialResults;
  let debounceTimer = null;
  let controller = null;
  let lastRendered = null;

  const escapeHTML = (value) =>
    String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");

  const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  const highlight = (value, query) => {
    const escaped = escapeHTML(value);
    const terms = String(query)
      .trim()
      .split(/\s+/)
      .filter((term) => term.length >= 2)
      .map(escapeRegExp);
    if (!terms.length) return escaped;
    return escaped.replace(new RegExp(`(${terms.join("|")})`, "gi"), "<mark>$1</mark>");
  };

  const pad = (number) => String(number).padStart(2, "0");

  const resultMarkup = (result) => {
    const kinds = { chapter: "Chapter", section: "Section", symbol: "Symbol" };
    const kind = kinds[result.kind] || "Answer";
    const kindClass =
      result.kind === "chapter" ? " is-chapter" : result.kind === "symbol" ? " is-symbol" : "";
    const meta =
      result.kind === "chapter"
        ? `${escapeHTML(result.category)} · ${escapeHTML(result.level)} · Chapter ${pad(result.chapter_number)}`
        : `${escapeHTML(result.category)} · ${escapeHTML(result.level)} · ${escapeHTML(result.chapter)}`;
    return `
      <a class="hb-result" href="${escapeHTML(result.url)}" data-hb-result>
        <span class="hb-result-kind${kindClass}">${kind}</span>
        <span class="hb-result-body">
          <span class="hb-result-title">${highlight(result.title, input.value)}</span>
          <span class="hb-result-meta">${meta}</span>
          <span class="hb-result-snippet">${highlight(result.snippet, input.value)}</span>
        </span>
        <span class="hb-result-arrow" aria-hidden="true">→</span>
      </a>`;
  };

  const showIdle = () => {
    results.innerHTML = idleMarkup;
    results.setAttribute("aria-busy", "false");
    lastRendered = "";
  };

  const showTooShort = () => {
    results.innerHTML = `
      <div class="hb-state">
        <span class="hb-state-mark" aria-hidden="true">…</span>
        <h2>One more character.</h2>
        <p>Search starts at two characters. Try “forms”, “orm” or “csrf”.</p>
      </div>`;
    results.setAttribute("aria-busy", "false");
    lastRendered = "";
  };

  const showEmpty = (query, suggestions = [], filtered = false, rawCount = 0) => {
    const suggestionsMarkup =
      !filtered && suggestions.length
        ? `
        <div class="hb-suggestions">
          <p class="hb-label">Did you mean</p>
          <div class="hb-suggestion-list">
            ${suggestions
              .map(
                (item) => `
                  <a href="${escapeHTML(item.url)}">
                    <strong>${escapeHTML(item.term)}</strong>
                    <span>${escapeHTML(item.chapter)}</span>
                  </a>`,
              )
              .join("")}
          </div>
        </div>`
        : "";
    const clearUrl = new URL(window.location.href);
    clearUrl.searchParams.delete("level");
    clearUrl.searchParams.delete("kind");
    const heading = filtered
      ? "No results match these filters."
      : `No answer matched “${escapeHTML(query)}”.`;
    const body = filtered
      ? `“${escapeHTML(query)}” has ${rawCount} answer${rawCount === 1 ? "" : "s"}, but none fit the current depth or result type.`
      : "Try the exception name, the Django file (<code>forms.py</code>, <code>urls.py</code>) or a shorter phrase. The official docs are linked at the end of every chapter.";
    results.innerHTML = `
      <div class="hb-state">
        <span class="hb-state-mark" aria-hidden="true">0</span>
        <h2>${heading}</h2>
        <p>${body}</p>
        ${suggestionsMarkup}
        <div class="hb-state-actions">
          ${
            filtered
              ? `<a class="btn btn-primary" href="${escapeHTML(clearUrl.pathname + clearUrl.search)}">Clear filters</a>`
              : `<a class="btn btn-primary" href="${escapeHTML(root.dataset.hbBrowse || "/handbook/")}">Browse all chapters</a>`
          }
        </div>
      </div>`;
    results.setAttribute("aria-busy", "false");
    lastRendered = "";
  };

  const showResults = (data) => {
    if (!data.count) {
      showEmpty(data.query, data.suggestions || [], data.filtered, data.raw_count || 0);
      return;
    }
    const rows = data.results.map(resultMarkup).join("");
    results.innerHTML = `
      <div class="hb-results-head">
        <div>
          <p class="hb-label">Search results</p>
          <h2>${data.count} answer${data.count === 1 ? "" : "s"} for “${escapeHTML(data.query)}”</h2>
        </div>
        <a class="hb-clear" href="${escapeHTML(root.dataset.hbBrowse || "/handbook/")}">Clear search</a>
      </div>
      <div class="hb-result-list">${rows}</div>`;
    results.setAttribute("aria-busy", "false");
    lastRendered = data.query;
  };

  const setBusy = (busy) => {
    results.setAttribute("aria-busy", busy ? "true" : "false");
  };

  const syncUrl = (query) => {
    try {
      const url = new URL(window.location.href);
      if (query) {
        url.searchParams.set("q", query);
      } else {
        url.searchParams.delete("q");
      }
      window.history.replaceState({}, "", url);
    } catch (_) {
      /* The search still works if history is unavailable. */
    }
  };

  const runSearch = async (query) => {
    syncUrl(query);
    if (!query) {
      showIdle();
      return;
    }
    if (query.length < 2) {
      showTooShort();
      return;
    }
    if (query === lastRendered) return;

    if (controller) controller.abort();
    controller = new AbortController();
    setBusy(true);

    try {
      const params = new URLSearchParams({ q: query });
      const current = new URL(window.location.href);
      for (const key of ["level", "kind"]) {
        const value = current.searchParams.get(key);
        if (value) params.set(key, value);
      }
      const response = await fetch(`${endpoint}?${params.toString()}`, {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Search returned ${response.status}`);
      const data = await response.json();
      if (query !== input.value.trim()) return; // A newer keystroke won the race.
      showResults(data);
    } catch (error) {
      if (error.name === "AbortError") return;
      results.innerHTML = `
        <div class="hb-state">
          <span class="hb-state-mark" aria-hidden="true">!</span>
          <h2>Search is unavailable.</h2>
          <p>Press Enter to run a normal page search.</p>
        </div>`;
      results.setAttribute("aria-busy", "false");
    }
  };

  const schedule = () => {
    window.clearTimeout(debounceTimer);
    const query = input.value.trim();
    if (!query) {
      syncUrl("");
      showIdle();
      return;
    }
    debounceTimer = window.setTimeout(() => runSearch(query), 140);
  };

  input.addEventListener("input", schedule);

  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      input.value = "";
      schedule();
      input.focus();
    }
  });

  form.addEventListener("submit", (event) => {
    if (!endpoint) return;
    event.preventDefault();
    window.clearTimeout(debounceTimer);
    runSearch(input.value.trim());
  });

  document.querySelectorAll("[data-hb-try]").forEach((button) => {
    button.addEventListener("click", () => {
      input.value = button.dataset.hbTry || "";
      schedule();
      input.focus();
      input.select();
    });
  });

  const resultLinks = () => Array.from(results.querySelectorAll("[data-hb-result]"));

  const focusResult = (direction) => {
    const links = resultLinks();
    if (!links.length) return;
    let index = links.indexOf(document.activeElement);
    if (index === -1) index = direction > 0 ? -1 : links.length;
    index = Math.min(links.length - 1, Math.max(0, index + direction));
    links.forEach((link) => link.classList.remove("is-focused"));
    links[index].classList.add("is-focused");
    links[index].focus({ preventScroll: true });
    links[index].scrollIntoView({ block: "nearest" });
  };

  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && !event.altKey && event.key.toLowerCase() === "k") {
      event.preventDefault();
      input.focus();
      input.select();
      return;
    }
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    const active = document.activeElement;
    const onResult = active instanceof Element && active.closest("[data-hb-result]");
    if (event.key === "ArrowDown" && (active === input || onResult)) {
      event.preventDefault();
      focusResult(1);
      return;
    }
    if (event.key === "ArrowUp" && (active === input || onResult)) {
      event.preventDefault();
      focusResult(-1);
      return;
    }
    if (event.key === "Escape" && onResult) {
      event.preventDefault();
      input.focus();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.key !== "/") return;
    const target = event.target;
    if (
      target instanceof Element &&
      (target.closest("input, textarea, select, [contenteditable=true]") ||
        target.closest(".hb-search"))
    ) {
      return;
    }
    event.preventDefault();
    input.focus();
    input.select();
  });

  // Keep the initial server-rendered results; only fetch when the user edits.
  if (input.value.trim().length >= 2) {
    lastRendered = input.value.trim();
  }
})();
