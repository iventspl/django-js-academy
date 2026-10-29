"""Samodzielny edytor wyzwań JS uruchamiany w sandboxowanym iframe."""

from __future__ import annotations

import json

from .models import JsChallenge


def _json_for_script(value) -> str:
    # Zapobiega przedwczesnemu zamknięciu <script> przez dane treści.
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def build_challenge_runner(challenge: JsChallenge) -> str:
    payload = {
        "slug": challenge.slug,
        "starter": challenge.starter_code,
        "solution": challenge.solution_code,
        "tests": challenge.tests,
        "hints": [line for line in challenge.hints.splitlines() if line.strip()],
    }
    data = _json_for_script(payload)
    return f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 14px; background: #fffdf7; color: #1b2a31;
  font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif; font-size: 13px; }}
.header {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 8px; }}
.kicker {{ margin: 0; color: #756200; font: 700 10px/1.3 monospace; letter-spacing: .08em; text-transform: uppercase; }}
h1 {{ margin: 0; font-size: 1.05rem; }}
.actions {{ display: flex; gap: 6px; flex-wrap: wrap; }}
button {{ min-height: 31px; padding: 5px 9px; border: 1px solid #1b2a31; border-radius: 6px;
  background: #f7df1e; color: #1b2a31; font: 700 10px/1.2 "Avenir Next", "Segoe UI", sans-serif; cursor: pointer; }}
button.secondary {{ background: #fff; }}
button:disabled {{ opacity: .5; cursor: wait; }}
textarea {{ width: 100%; min-height: 174px; padding: 10px; resize: vertical; border: 1px solid #cfc3ad;
  border-radius: 7px; background: #15232b; color: #e9f2ec; font: 11px/1.55 "SFMono-Regular", Consolas, monospace; tab-size: 2; }}
.results {{ margin-top: 9px; padding: 0; list-style: none; }}
.results li {{ margin: 3px 0; padding: 5px 7px; border-radius: 5px; background: #f5eedf; font-size: 11px; }}
.results li.ok {{ background: #e4f3e8; color: #205c43; }}
.results li.bad {{ background: #fae8e2; color: #8e3522; }}
pre {{ margin: 8px 0 0; padding: 9px; max-height: 110px; overflow: auto; border-radius: 6px;
  background: #f2ead9; color: #34443d; font: 10px/1.5 monospace; white-space: pre-wrap; }}
.hint {{ margin: 7px 0 0; padding: 7px 9px; border-left: 3px solid #f7df1e; background: #fff6c9; font-size: 11px; }}
.muted {{ color: #75857f; font-size: 10px; }}
.hidden {{ display: none; }}
</style></head>
<body>
<div class="header"><div><p class="kicker">Wyzwanie · uruchom testy</p><h1>Twój kod</h1></div>
<div class="actions"><button id="run">Uruchom testy</button><button class="secondary" id="hint">Podpowiedź</button>
<button class="secondary" id="reset">Reset</button><button class="secondary" id="solution">Rozwiązanie</button></div></div>
<textarea id="code" spellcheck="false" aria-label="Edytor kodu"></textarea>
<ul class="results" id="results"></ul>
<pre id="console" class="hidden"></pre>
<div id="hint-box" class="hint hidden"></div>
<p class="muted">Kod działa wyłącznie w tej piaskownicy. Jeśli pętla się zapętli, odśwież stronę.</p>
<script>
const data = {data};
const codeEl = document.getElementById("code");
const resultsEl = document.getElementById("results");
const consoleEl = document.getElementById("console");
const hintBox = document.getElementById("hint-box");
codeEl.value = data.starter;
let hintIndex = -1;

function normalize(value) {{
  if (Array.isArray(value)) return value.map(normalize);
  if (value && typeof value === "object") {{
    const out = {{}};
    for (const key of Object.keys(value).sort()) out[key] = normalize(value[key]);
    return out;
  }}
  return value;
}}
function same(a, b) {{
  return JSON.stringify(normalize(a)) === JSON.stringify(normalize(b));
}}
function showConsole(lines) {{
  if (!lines.length) {{ consoleEl.classList.add("hidden"); return; }}
  consoleEl.classList.remove("hidden");
  consoleEl.textContent = lines.join("\\n");
}}
function render(rows) {{
  resultsEl.innerHTML = "";
  for (const row of rows) {{
    const li = document.createElement("li");
    li.className = row.ok ? "ok" : "bad";
    li.textContent = (row.ok ? "✓ " : "✗ ") + row.name + (row.ok ? "" : " · oczekiwano: " + JSON.stringify(row.expected) + " · otrzymano: " + JSON.stringify(row.actual));
    resultsEl.appendChild(li);
  }}
}}
async function run() {{
  const logs = [];
  const originalLog = console.log;
  console.log = (...args) => logs.push(args.map(String).join(" "));
  try {{
    const factory = new Function(codeEl.value + "\\nreturn typeof solve === 'function' ? solve : null;");
    const solve = factory();
    if (!solve) throw new Error("Zdefiniuj funkcję solve(...).");
    const rows = [];
    for (const test of data.tests) {{
      let actual;
      try {{ actual = await solve(...test.args); }}
      catch (error) {{ actual = "Błąd: " + error.message; }}
      rows.push({{ name: test.name, expected: test.expected, actual, ok: same(actual, test.expected) }});
    }}
    render(rows);
    const passed = rows.every((row) => row.ok);
    if (passed) {{
      const note = document.createElement("li");
      note.className = "ok";
      note.textContent = "Wszystkie testy przechodzą. Wróć do lekcji i oznacz wyzwanie.";
      resultsEl.appendChild(note);
      window.parent.postMessage({{ type: "js-challenge-passed", slug: data.slug }}, "*");
    }}
  }} catch (error) {{
    render([{{ name: error.message, expected: "poprawny kod", actual: "wyjątek", ok: false }}]);
  }} finally {{
    console.log = originalLog;
    showConsole(logs);
  }}
}}
document.getElementById("run").addEventListener("click", run);
document.getElementById("reset").addEventListener("click", () => {{ codeEl.value = data.starter; resultsEl.innerHTML = ""; }});
document.getElementById("solution").addEventListener("click", () => {{ codeEl.value = data.solution; resultsEl.innerHTML = ""; }});
document.getElementById("hint").addEventListener("click", () => {{
  if (!data.hints.length) return;
  hintIndex = (hintIndex + 1) % data.hints.length;
  hintBox.textContent = data.hints[hintIndex];
  hintBox.classList.remove("hidden");
}});
</script>
</body></html>"""
