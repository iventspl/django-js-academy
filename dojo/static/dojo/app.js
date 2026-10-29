/* Django Quest — small, dependency-free interactions. */
(function () {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  /* ---------- Toasts ---------- */
  const toasts = $(".toast-stack");
  if (toasts) {
    window.setTimeout(() => {
      toasts.classList.add("is-leaving");
      window.setTimeout(() => toasts.remove(), 350);
    }, 5200);
  }

  /* ---------- Quiz keyboard + selection ---------- */
  const quizForm = $("[data-quiz-form]");
  if (quizForm) {
    const inputs = $$("[data-answer-input]", quizForm);

    const markSelected = (input) => {
      $$(".answer-option", quizForm).forEach((option) => {
        option.classList.remove("is-selected");
      });
      const label = input.closest(".answer-option");
      if (label) label.classList.add("is-selected");
    };

    inputs.forEach((input, index) => {
      input.addEventListener("change", () => markSelected(input));
      input.dataset.index = String(index + 1);
    });

    document.addEventListener("keydown", (event) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const tag = (event.target.tagName || "").toLowerCase();
      const type = (event.target.type || "").toLowerCase();
      if (["textarea", "select"].includes(tag)) return;
      if (tag === "input" && !["radio", "checkbox"].includes(type)) return;

      if (/^[1-4]$/.test(event.key)) {
        const input = inputs[Number(event.key) - 1];
        if (!input) return;
        event.preventDefault();
        input.checked = true;
        markSelected(input);
      }

      if (event.key === "Enter" && !event.target.closest("a, button, summary")) {
        const selected = inputs.find((input) => input.checked);
        if (selected) {
          event.preventDefault();
          quizForm.requestSubmit();
        }
      }
    });
  }

  /* ---------- Enter advances after feedback ---------- */
  const nextButton = $("[data-next-button]");
  if (nextButton) {
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.target instanceof Element && event.target.closest("a, button, input, textarea, select, summary")) return;
      event.preventDefault();
      nextButton.click();
    });
  }

  /* ---------- Flashcard flip ---------- */
  const stage = $("[data-study-stage]");  if (stage) {
    const card = $("[data-flashcard]", stage);
    const front = $("[data-card-front]", stage);
    const back = $("[data-card-back]", stage);
    const flipButton = $("[data-flip-button]", stage);
    const ratingForm = $("[data-rating-form]", stage);

    const reveal = (focusRatings) => {
      stage.dataset.revealed = "true";
      if (card) card.classList.add("is-revealed");
      if (front) front.setAttribute("aria-hidden", "true");
      if (back) back.setAttribute("aria-hidden", "false");
      try {
        const url = new URL(window.location.href);
        url.searchParams.set("reveal", "1");
        window.history.replaceState({}, "", url);
      } catch (_) {
        /* History is a nicety; the card still flips. */
      }
      if (focusRatings) {
        const firstRating = $("[data-rating-form] .rating-btn", stage);
        if (firstRating) {
          window.setTimeout(() => firstRating.focus({ preventScroll: true }), 450);
        }
      }
    };

    if (stage.dataset.revealed === "true") {
      reveal(false);
    }

    if (flipButton) {
      flipButton.addEventListener("click", (event) => {
        event.preventDefault();
        reveal(false);
      });
    }

    document.addEventListener("keydown", (event) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const tag = (event.target.tagName || "").toLowerCase();
      if (["input", "textarea", "select"].includes(tag)) return;

      const isRevealed = stage.dataset.revealed === "true";

      if ((event.key === " " || event.key === "Spacebar") && !isRevealed) {
        if (event.target.closest("a, button, summary, details")) return;
        event.preventDefault();
        reveal(false);
        return;
      }

      if (isRevealed && ratingForm && /^[1-4]$/.test(event.key)) {
        const buttons = $$(".rating-btn", ratingForm);
        const button = buttons[Number(event.key) - 1];
        if (!button) return;
        event.preventDefault();
        button.click();
      }
    });
  }

  /* ---------- Destructive action confirmation ---------- */
  $$("[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.dataset.confirm;
      if (message && !window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  /* ---------- Field guide: copy code blocks ---------- */
  $$("[data-copy-code]").forEach((button) => {
    button.addEventListener("click", async () => {
      const block = button.closest(".code-block");
      const code = block ? $("pre code", block) : null;
      if (!code) return;
      const text = code.textContent;
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
        } else {
          const helper = document.createElement("textarea");
          helper.value = text;
          helper.style.position = "fixed";
          helper.style.opacity = "0";
          document.body.appendChild(helper);
          helper.select();
          document.execCommand("copy");
          helper.remove();
        }
        button.textContent = "Copied";
        window.setTimeout(() => {
          button.textContent = "Copy";
        }, 1600);
      } catch (_) {
        button.textContent = "Select & copy";
      }
    });
  });

  /* ---------- Open a recipe when linked by hash ---------- */
  if (window.location.hash.startsWith("#recipe-")) {
    const target = document.querySelector(window.location.hash);
    if (target && target.tagName === "DETAILS") {
      target.open = true;
      target.scrollIntoView({ block: "start" });
    }
  }

  /* ---------- Prevent accidental double submits ---------- */
  $$("[data-rating-form]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (form.dataset.submitting === "true") {
        event.preventDefault();
        return;
      }
      form.dataset.submitting = "true";
      form.setAttribute("aria-busy", "true");
      $$(".rating-btn", form).forEach((button) => {
        // Keep buttons enabled: a disabled submit button is not included in
        // the submitted form data, so the server would never receive `rating`.
        button.classList.add("is-loading");
      });
    });
  });
})();
