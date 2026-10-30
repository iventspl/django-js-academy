"""Real-world MVC project walkthroughs for JS Akademia.

Content is Polish; source code is English. Each step contains hidden hints and a
complete answer for that step so a learner can compare after trying it alone.
"""

from __future__ import annotations

from textwrap import dedent


def step(
    *,
    slug: str,
    title: str,
    goal: str,
    why: str,
    filename: str,
    minutes: int,
    tasks: list[str],
    hints: list[str],
    answer: str,
    explain: str,
    checkpoint: list[str],
) -> dict:
    return {
        "slug": slug,
        "title": title,
        "goal": goal,
        "why": why,
        "filename": filename,
        "minutes": minutes,
        "tasks": tasks,
        "hints": hints,
        "answer": dedent(answer).strip(),
        "explain": explain,
        "checkpoint": checkpoint,
    }


PROJECTS = [
    {
        "slug": "sklep-internetowy",
        "title": "Sklep internetowy",
        "subtitle": "Katalog, koszyk, kasa i trwały stan — kompletny sklep w czystym MVC.",
        "eyebrow": "Projekt 01 · e-commerce",
        "glyph": "01",
        "accent": "#f7df1e",
        "preview": "js_academy/shop-preview.png",
        "level": "średni",
        "duration": "8–10 godzin",
        "stack": ["Vanilla JS", "MVC", "localStorage", "Fetch API"],
        "summary": (
            "Zbudujesz sklep, który naprawdę da się używać: produkty, filtrowanie, "
            "sortowanie, koszyk, ilości, kasa i koszyk przeżywający odświeżenie strony."
        ),
        "outcome": (
            "Po ośmiu krokach masz aplikację z jednym obiektem stanu, czystymi funkcjami filtrującymi, "
            "widokami bez innerHTML i kontrolerami, które nie mieszają się z DOM."
        ),
        "features": [
            "katalog produktów z wyszukiwaniem i filtrami",
            "sortowanie po cenie i nazwie",
            "koszyk z ilościami i podsumowaniem",
            "trwałość koszyka w localStorage",
            "kasa z walidacją i podsumowaniem zamówienia",
            "testy funkcji filtrujących i dostępność klawiaturowa",
        ],
        "constraints": [
            "Bez frameworka i bez biblioteki UI.",
            "Bez wklejania HTML przez innerHTML.",
            "Stan aplikacji jest jednym obiektem; funkcje filtrujące nie mutują danych.",
            "Mobile-first: każdy widok działa od 360 px.",
        ],
        "files": [
            "index.html",
            "src/model.js",
            "src/catalog.js",
            "src/store.js",
            "src/catalog-view.js",
            "src/cart.js",
            "src/checkout.js",
            "src/app.js",
            "tests/catalog.test.js",
        ],
        "shell": """<!doctype html>
<html lang="pl">
  <head>
    <meta charset="utf-8">
    <meta
      name="viewport"
      content="width=device-width, initial-scale=1"
    >
    <title>Sklep internetowy</title>
  </head>
  <body>
    <header>
      <h1>Sklep</h1>
      <button type="button" data-go-cart>
        Koszyk
      </button>
    </header>
    <main data-app></main>
    <script
      type="module"
      src="./src/app.js"
    ></script>
  </body>
</html>""",
        "brief": (
            "Wyobraź sobie mały sklep z kawą i akcesoriami. Nie potrzebujesz backendu, "
            "żeby przejść cały przepływ: dane → funkcje filtrujące → widok → akcja → nowy stan → render. "
            "Właśnie ten przepływ jest celem projektu, nie sam wygląd sklepu."
        ),
        "steps": [
            step(
                slug="model-danych",
                title="Model danych i pieniądze w groszach",
                goal=(
                    "Zdefiniuj produkty, linie koszyka i operacje na pieniądzach tak, "
                    "żeby reszta aplikacji nie musiała znać formatu cen."
                ),
                why=(
                    "Ceny w liczbach zmiennoprzecinkowych potrafią dać 0.30000000000000004. "
                    "W modelu danych trzymamy grosze jako liczby całkowite, a formatowanie robimy tylko w widoku."
                ),
                filename="src/model.js",
                minutes=45,
                tasks=[
                    "Utwórz funkcje toGrosze, formatMoney i lineTotal.",
                    "Dodaj createCartLine, cartTotal i cartCount.",
                    "Napisz trzy przypadki brzegowe: pusta cena, zero sztuk, ujemna cena.",
                ],
                hints=[
                    "Zamień przecinek na kropkę przed Number(), bo użytkownik może wpisać 19,99.",
                    "Nie formatuj ceny w modelu. Model zwraca liczbę groszy; formatMoney jest funkcją prezentacji.",
                ],
                answer="""
// src/model.js
const CURRENCY = "PLN";
const formatter = new Intl.NumberFormat("pl-PL", {
  style: "currency",
  currency: CURRENCY,
});

export function toGrosze(value) {
  const normalized = String(value).trim().replace(",", ".");
  const amount = Math.round(Number(normalized) * 100);
  if (!Number.isFinite(amount) || amount < 0) {
    throw new Error("Price must be a non-negative number");
  }
  return amount;
}

export function formatMoney(grosze) {
  return formatter.format(grosze / 100);
}

export function createCartLine(product, quantity = 1) {
  if (quantity < 1) throw new Error("Quantity must be at least 1");
  return {
    productId: product.id,
    name: product.name,
    unitPrice: product.price,
    quantity,
  };
}

export function lineTotal(line) {
  return line.unitPrice * line.quantity;
}

export function cartTotal(lines) {
  return lines.reduce((sum, line) => sum + lineTotal(line), 0);
}

export function cartCount(lines) {
  return lines.reduce((sum, line) => sum + line.quantity, 0);
}
""",
                explain=(
                    "To jest pełne rozwiązanie pierwszego kroku. Produkt ma cenę w groszach, "
                    "linia koszyka przechowuje cenę z chwili dodania, a formatowanie jest osobną funkcją."
                ),
                checkpoint=[
                    "toGrosze(\"19,99\") zwraca 1999.",
                    "cartTotal([]) zwraca 0, a nie NaN.",
                    "formatMoney(1999) wyświetla kwotę w PLN.",
                ],
            ),
            step(
                slug="warstwa-danych-i-filtry",
                title="Warstwa danych i czyste filtry",
                goal=(
                    "Oddziel pobieranie danych od filtrowania. Widok ma dostać już gotową listę "
                    "produktów, a nie zajmować się query, kategorią i sortowaniem."
                ),
                why=(
                    "Funkcje filtrujące to najbardziej testowalna część aplikacji. Jeśli przyjmują dane i stan, "
                    "a zwracają nową listę, możesz je sprawdzić bez przeglądarki."
                ),
                filename="src/catalog.js",
                minutes=60,
                tasks=[
                    "Zbuduj loadProducts z bezpiecznym fallbackiem, gdy fetch zawiedzie.",
                    "Napisz matchesQuery, filterProducts i sortProducts jako funkcje czyste.",
                    "Dodaj selectProducts, które składa filtr, sortowanie i paginację.",
                ],
                hints=[
                    "sortProducts ma kopiować tablicę: [...products].sort(...). Inaczej mutujesz dane wejściowe.",
                    "Sortowanie po cenie rób na groszach, nie na sformatowanych stringach.",
                ],
                answer="""
// src/catalog.js
const FALLBACK_PRODUCTS = [
  { id: "espresso", name: "Espresso", category: "coffee", price: 1299 },
  { id: "latte", name: "Latte", category: "coffee", price: 1599 },
  { id: "grinder", name: "Hand grinder", category: "gear", price: 18900 },
];

export function normalizeProduct(raw) {
  return {
    id: String(raw.id),
    name: String(raw.name),
    category: String(raw.category),
    price: Math.max(0, Math.round(Number(raw.price))),
    description: String(raw.description ?? ""),
  };
}

export async function loadProducts(fetchImpl = fetch) {
  try {
    const response = await fetchImpl("/data/products.json");
    if (!response.ok) throw new Error("Products request failed");
    const data = await response.json();
    return data.map(normalizeProduct);
  } catch (_) {
    return FALLBACK_PRODUCTS.map(normalizeProduct);
  }
}

export function matchesQuery(product, query) {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return `${product.name} ${product.description}`.toLowerCase().includes(needle);
}

export function filterProducts(products, state) {
  return products.filter((product) => {
    const categoryOk =
      state.currentCategory === "all" ||
      product.category === state.currentCategory;
    return categoryOk && matchesQuery(product, state.currentQuery);
  });
}

export function sortProducts(products, sort) {
  const copy = [...products];
  const direction = sort.direction === "desc" ? -1 : 1;
  copy.sort((a, b) => {
    if (sort.key === "price") return (a.price - b.price) * direction;
    return a.name.localeCompare(b.name, "pl") * direction;
  });
  return copy;
}

export function selectProducts(products, state) {
  const filtered = filterProducts(products, state);
  const sorted = sortProducts(filtered, state.currentSort);
  const start = (state.currentPage - 1) * state.pageSize;
  return {
    items: sorted.slice(start, start + state.pageSize),
    total: sorted.length,
    pages: Math.max(1, Math.ceil(sorted.length / state.pageSize)),
  };
}
""",
                explain=(
                    "Warstwa danych odpowiada za wejście danych, a funkcje filtrujące za decyzję, co pokazać. "
                    "selectProducts nie dotyka DOM ani localStorage, więc jest łatwe do przetestowania."
                ),
                checkpoint=[
                    "selectProducts nie zmienia oryginalnej tablicy.",
                    "Puste query zwraca wszystkie produkty z kategorii.",
                    "Nieudany fetch nadal daje listę fallback, więc strona nie jest pusta.",
                ],
            ),
            step(
                slug="stan-i-router",
                title="Jeden stan i router",
                goal=(
                    "Połącz widok, filtr, sortowanie, koszyk i kasę w jednym obiekcie stanu. "
                    "Adres URL ma mówić, który widok jest aktywny."
                ),
                why=(
                    "Gdy currentView, currentQuery, currentSort, currentPage i cart są osobnymi zmiennymi, "
                    "każda akcja musi pamiętać o ich synchronizacji. Jeden obiekt i czysta aktualizacja "
                    "usuwają całą klasę błędów."
                ),
                filename="src/store.js",
                minutes=60,
                tasks=[
                    "Zdefiniuj createInitialState z polami currentView, currentQuery, currentSort i currentPage.",
                    "Napisz updateState, które przy zmianie query lub kategorii resetuje stronę do 1.",
                    "Dodaj parseRoute i toHash dla #/, #/koszyk i #/checkout.",
                ],
                hints=[
                    "currentSort to obiekt { key, direction }, nie string. Dzięki temu widok nie zgaduje kierunku.",
                    "Nie trzymaj tablicy produktów w stanie, jeśli jest tylko kopią danych w pamięci; trzymaj ją osobno.",
                ],
                answer="""
// src/store.js
export function createInitialState() {
  return {
    currentView: "catalog",
    currentQuery: "",
    currentCategory: "all",
    currentSort: { key: "name", direction: "asc" },
    currentPage: 1,
    pageSize: 6,
    cart: [],
    checkout: null,
  };
}

export function updateState(state, patch) {
  const next = { ...state, ...patch };

  if ("currentQuery" in patch || "currentCategory" in patch) {
    next.currentPage = 1;
  }
  if ("currentSort" in patch) {
    next.currentPage = 1;
  }
  return next;
}

export function parseRoute(hash = window.location.hash) {
  const clean = hash.replace(/^#/, "") || "/";
  if (clean === "/checkout") return { view: "checkout" };
  if (clean === "/koszyk") return { view: "cart" };
  return { view: "catalog" };
}

export function toHash(view) {
  if (view === "cart") return "#/koszyk";
  if (view === "checkout") return "#/checkout";
  return "#/";
}
""",
                explain=(
                    "To jest pełne rozwiązanie kroku stanu. Aktualizacja jest czysta: dostaje stan i patch, "
                    "zwraca nowy obiekt. Router jest mały, bo na razie obsługuje trzy widoki."
                ),
                checkpoint=[
                    "updateState(state, { currentQuery: \"x\" }) ustawia currentPage na 1.",
                    "parseRoute(\"#/koszyk\") zwraca view: \"cart\".",
                    "Nie ma globalnej zmiennej currentView poza obiektem stanu.",
                ],
            ),
            step(
                slug="widok-katalogu",
                title="Widok katalogu bez innerHTML",
                goal=(
                    "Zbuduj karty produktów, filtry i pusty stan przez DOM API. "
                    "Widok ma tylko czytać stan i wywoływać akcje, nie zmieniać danych."
                ),
                why=(
                    "innerHTML z danymi użytkownika to prosta droga do XSS. Poza tym trudno nim zarządzać: "
                    "każdy render niszczy focus i event listenery. DOM API jest bezpieczniejsze i bardziej przewidywalne."
                ),
                filename="src/catalog-view.js",
                minutes=75,
                tasks=[
                    "Zbuduj renderCatalog(root, products, state, actions).",
                    "Dodaj wyszukiwarkę, select kategorii i select sortowania.",
                    "Obsłuż pusty wynik oraz komunikaty aria-live.",
                ],
                hints=[
                    "Użyj replaceChildren, żeby wyczyścić listę i wstawić nowe karty.",
                    "Przycisk Dodaj do koszyka powinien mieć data-product-id; nie twórz osobnego listenera dla każdej karty.",
                ],
                answer="""
// src/catalog-view.js
import { formatMoney } from "./model.js";
import { selectProducts } from "./catalog.js";

export function renderCatalog(root, products, state, actions) {
  const result = selectProducts(products, state);

  const toolbar = document.createElement("div");
  toolbar.className = "catalog-toolbar";

  const search = document.createElement("input");
  search.type = "search";
  search.placeholder = "Szukaj produktu…";
  search.value = state.currentQuery;
  search.setAttribute("aria-label", "Szukaj produktu");
  search.addEventListener("input", (event) => {
    actions.onQuery(event.target.value);
  });

  const category = document.createElement("select");
  category.setAttribute("aria-label", "Kategoria");
  for (const [value, label] of [
    ["all", "Wszystkie"],
    ["coffee", "Kawa"],
    ["gear", "Akcesoria"],
  ]) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = state.currentCategory === value;
    category.append(option);
  }
  category.addEventListener("change", (event) => {
    actions.onCategory(event.target.value);
  });

  const sort = document.createElement("select");
  sort.setAttribute("aria-label", "Sortowanie");
  for (const [value, label] of [
    ["name:asc", "Nazwa A–Z"],
    ["price:asc", "Cena rosnąco"],
    ["price:desc", "Cena malejąco"],
  ]) {
    const [key, direction] = value.split(":");
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected =
      state.currentSort.key === key && state.currentSort.direction === direction;
    sort.append(option);
  }
  sort.addEventListener("change", (event) => {
    const [key, direction] = event.target.value.split(":");
    actions.onSort({ key, direction });
  });

  toolbar.append(search, category, sort);

  const grid = document.createElement("div");
  grid.className = "product-grid";
  grid.replaceChildren(
    ...result.items.map((product) => renderProductCard(product, actions))
  );

  const empty = document.createElement("p");
  empty.className = "catalog-empty";
  empty.setAttribute("role", "status");
  empty.textContent =
    result.total === 0
      ? "Brak produktów dla tych filtrów. Wyczyść wyszukiwanie."
      : `Pokazano ${result.items.length} z ${result.total} produktów.`;

  root.replaceChildren(toolbar, grid, empty);
}

function renderProductCard(product, actions) {
  const card = document.createElement("article");
  card.className = "product-card";

  const title = document.createElement("h3");
  title.textContent = product.name;

  const price = document.createElement("p");
  price.className = "product-price";
  price.textContent = formatMoney(product.price);

  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn btn-small";
  button.textContent = "Dodaj do koszyka";
  button.addEventListener("click", () => actions.onAdd(product.id));

  card.append(title, price, button);
  return card;
}
""",
                explain=(
                    "To jest pełny widok katalogu dla tego kroku. Każdy element powstaje przez createElement, "
                    "a akcje są przekazane jako obiekt funkcji. Widok nie wie, skąd biorą się produkty."
                ),
                checkpoint=[
                    "W kodzie widoku nie ma innerHTML.",
                    "Wpisanie tekstu w search wywołuje akcję, a nie bezpośrednio zmienia stan.",
                    "Pusty wynik pokazuje sensowny komunikat, nie pustą siatkę.",
                ],
            ),
            step(
                slug="koszyk-i-localstorage",
                title="Koszyk, ilości i localStorage",
                goal=(
                    "Dodawaj produkty, zmieniaj ilości, usuwaj linie i zapisuj koszyk tak, "
                    "żeby przetrwał odświeżenie strony."
                ),
                why=(
                    "Koszyk to nie tylko tablica. To reguły: ten sam produkt zwiększa ilość, "
                    "zero usuwa linię, a stan z pamięci może być stary lub uszkodzony. Te reguły muszą być w jednym miejscu."
                ),
                filename="src/cart.js",
                minutes=75,
                tasks=[
                    "Napisz addToCart, setQuantity i removeFromCart jako czyste funkcje.",
                    "Dodaj małą warstwę dostępu do pamięci z wersją i bezpiecznym odczytem.",
                    "Zbuduj renderCart z podsumowaniem i formularzem ilości.",
                ],
                hints=[
                    "Nie zapisuj w localStorage całego stanu aplikacji. Zapisz tylko koszyk i wersję.",
                    "JSON.parse może rzucić wyjątkiem; złap błąd i wróć do pustego koszyka.",
                ],
                answer="""
// src/cart.js
import { createCartLine, cartTotal, cartCount, formatMoney } from "./model.js";

const KEY = "django-quest-shop-cart";
const VERSION = 1;

export function addToCart(state, product) {
  const existing = state.cart.find((line) => line.productId === product.id);
  const cart = existing
    ? state.cart.map((line) =>
        line.productId === product.id
          ? { ...line, quantity: line.quantity + 1 }
          : line
      )
    : [...state.cart, createCartLine(product)];
  return { ...state, cart };
}

export function setQuantity(state, productId, quantity) {
  const safe = Math.max(0, Math.floor(Number(quantity) || 0));
  const cart =
    safe === 0
      ? state.cart.filter((line) => line.productId !== productId)
      : state.cart.map((line) =>
          line.productId === productId ? { ...line, quantity: safe } : line
        );
  return { ...state, cart };
}

export function removeFromCart(state, productId) {
  return setQuantity(state, productId, 0);
}

export function createCartStorage(storage = window.localStorage) {
  return {
    read() {
      try {
        const raw = storage.getItem(KEY);
        if (!raw) return [];
        const data = JSON.parse(raw);
        if (data.version !== VERSION || !Array.isArray(data.lines)) return [];
        return data.lines;
      } catch (_) {
        return [];
      }
    },
    write(lines) {
      try {
        storage.setItem(KEY, JSON.stringify({ version: VERSION, lines }));
      } catch (_) {
        // Storage can be full or disabled; the in-memory cart still works.
      }
    },
  };
}

export function renderCart(root, state, actions) {
  if (!state.cart.length) {
    root.textContent = "Koszyk jest pusty. Wróć do katalogu.";
    return;
  }

  const list = document.createElement("ul");
  list.className = "cart-lines";
  for (const line of state.cart) {
    const item = document.createElement("li");
    const name = document.createElement("strong");
    name.textContent = line.name;

    const qty = document.createElement("input");
    qty.type = "number";
    qty.min = "0";
    qty.value = String(line.quantity);
    qty.setAttribute("aria-label", `Ilość: ${line.name}`);
    qty.addEventListener("change", () => actions.onQuantity(line.productId, qty.value));

    const total = document.createElement("span");
    total.textContent = formatMoney(line.unitPrice * line.quantity);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Usuń";
    remove.addEventListener("click", () => actions.onRemove(line.productId));

    item.append(name, qty, total, remove);
    list.append(item);
  }

  const summary = document.createElement("p");
  summary.className = "cart-summary";
  summary.textContent = `Razem: ${formatMoney(cartTotal(state.cart))} · ${cartCount(
    state.cart
  )} szt.`;

  root.replaceChildren(list, summary);
}
""",
                explain=(
                    "To jest pełne rozwiązanie koszyka. Funkcje koszyka są czyste, a localStorage jest "
                    "ukryte za tą warstwą. Dzięki temu możesz podmienić pamięć w testach."
                ),
                checkpoint=[
                    "Dodanie tego samego produktu zwiększa quantity, nie tworzy drugiej linii.",
                    "Ustawienie ilości 0 usuwa produkt.",
                    "Uszkodzony JSON w localStorage nie wywala aplikacji.",
                ],
            ),
            step(
                slug="kasa-i-walidacja",
                title="Kasa i walidacja zamówienia",
                goal=(
                    "Zbierz dane klienta, zwaliduj je bez biblioteki i zbuduj obiekt zamówienia, "
                    "który mógłby trafić do API."
                ),
                why=(
                    "Walidacja w kontrolerze jest łatwa do przetestowania i nie zależy od DOM. "
                    "Widok pokazuje tylko błędy, które dostanie z funkcji walidującej."
                ),
                filename="src/checkout.js",
                minutes=60,
                tasks=[
                    "Napisz validateCheckout(values) zwracające obiekt błędów.",
                    "Dodaj buildOrder(cart, customer) i submitOrder z obsługą błędu sieci.",
                    "Zbuduj formularz kasy z komunikatami przy polach.",
                ],
                hints=[
                    "Nie waliduj tylko przy submit. Wywołuj tę samą funkcję przy blur i przy wysyłce.",
                    "E-mail sprawdzaj prostym testem, ale nie obiecuj, że to pełna walidacja RFC.",
                ],
                answer="""
// src/checkout.js
export function validateCheckout(values) {
  const errors = {};
  if (!values.name || values.name.trim().length < 2) {
    errors.name = "Podaj imię i nazwisko.";
  }
  if (!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(values.email ?? "")) {
    errors.email = "Podaj poprawny adres e-mail.";
  }
  if (!/^\\d{2}-?\\d{3}$/.test((values.postalCode ?? "").trim())) {
    errors.postalCode = "Kod pocztowy w formacie 00-000.";
  }
  if (!values.address || values.address.trim().length < 5) {
    errors.address = "Podaj ulicę i numer.";
  }
  return errors;
}

export function buildOrder(cart, customer) {
  const lines = cart.map((line) => ({
    productId: line.productId,
    quantity: line.quantity,
    unitPrice: line.unitPrice,
  }));
  return {
    customer: {
      name: customer.name.trim(),
      email: customer.email.trim(),
      address: customer.address.trim(),
      postalCode: customer.postalCode.trim(),
    },
    lines,
    total: lines.reduce(
      (sum, line) => sum + line.unitPrice * line.quantity,
      0
    ),
  };
}

export async function submitOrder(order, fetchImpl = fetch) {
  const response = await fetchImpl("/api/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(order),
  });
  if (!response.ok) throw new Error("Order could not be submitted");
  return response.json();
}

export function bindCheckout(form, getCart, onSuccess) {
  const errors = document.createElement("div");
  errors.className = "form-errors";
  errors.setAttribute("role", "alert");
  form.append(errors);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(form));
    const found = validateCheckout(values);
    errors.replaceChildren();
    if (Object.keys(found).length) {
      for (const message of Object.values(found)) {
        const item = document.createElement("p");
        item.textContent = message;
        errors.append(item);
      }
      form.querySelector("input")?.focus();
      return;
    }
    const order = buildOrder(getCart(), values);
    await onSuccess(order);
  });
}
""",
                explain=(
                    "To jest pełna walidacja i budowa zamówienia dla tego kroku. Formularz dostaje "
                    "tylko komunikaty; nie zawiera reguł biznesowych."
                ),
                checkpoint=[
                    "validateCheckout({}) zwraca cztery błędy.",
                    "buildOrder nie zawiera nazw produktów, tylko stabilne id i ceny.",
                    "Nieudane zapytanie pokazuje błąd, nie czyści koszyka.",
                ],
            ),
            step(
                slug="skladanie-aplikacji",
                title="Składanie aplikacji i odtwarzanie koszyka",
                goal=(
                    "Połącz model, funkcje filtrujące, widoki i kontrolery w jeden przepływ. "
                    "Po odświeżeniu strony odtwórz koszyk i aktualny widok."
                ),
                why=(
                    "MVC nie jest skończone, dopóki nie ma jednego miejsca, które wie, jak złożyć części. "
                    "Start aplikacji ma być nudny: odczytaj stan, podłącz akcje, wyrenderuj."
                ),
                filename="src/app.js",
                minutes=75,
                tasks=[
                    "Utwórz punkt startowy z jednym obiektem state i jednym render().",
                    "Podłącz hashchange, storage i akcje koszyka.",
                    "Dodaj obsługę błędów startowych i stan ładowania.",
                ],
                hints=[
                    "render() nie powinien tworzyć nowych danych ani czytać localStorage przy każdym wywołaniu.",
                    "Po każdej akcji zapisz koszyk, ale nie zapisuj całego stanu ani query.",
                ],
                answer="""
// src/app.js
import { loadProducts } from "./catalog.js";
import { createInitialState, updateState, parseRoute, toHash } from "./store.js";
import { renderCatalog } from "./catalog-view.js";
import {
  addToCart,
  setQuantity,
  removeFromCart,
  createCartStorage,
  renderCart,
} from "./cart.js";
import { bindCheckout } from "./checkout.js";

const root = document.querySelector("[data-app]");
const storage = createCartStorage();
let state = { ...createInitialState(), cart: storage.read() };
let products = [];

function setState(patch) {
  const previousCart = state.cart;
  state = updateState(state, patch);
  if (state.cart !== previousCart) storage.write(state.cart);
  render();
}

function render() {
  if (!root) return;
  root.dataset.view = state.currentView;

  if (state.currentView === "catalog") {
    renderCatalog(root, products, state, {
      onQuery: (value) => setState({ currentQuery: value }),
      onCategory: (value) => setState({ currentCategory: value }),
      onSort: (value) => setState({ currentSort: value }),
      onAdd: (id) => {
        const product = products.find((item) => item.id === id);
        if (product) setState({ cart: addToCart(state, product).cart });
      },
    });
    return;
  }

  if (state.currentView === "cart") {
    renderCart(root, state, {
      onQuantity: (id, value) => setState({ cart: setQuantity(state, id, value).cart }),
      onRemove: (id) => setState({ cart: removeFromCart(state, id).cart }),
    });
  }
}

async function boot() {
  root.textContent = "Ładowanie produktów…";
  products = await loadProducts();
  const route = parseRoute();
  state = { ...state, currentView: route.view };
  window.addEventListener("hashchange", () => {
    state = { ...state, currentView: parseRoute().view };
    render();
  });
  document.querySelector("[data-go-cart]")?.addEventListener("click", () => {
    window.location.hash = toHash("cart");
  });
  render();
}

boot().catch(() => {
  root.textContent = "Nie udało się uruchomić sklepu. Odśwież stronę.";
});
""",
                explain=(
                    "To jest pełny start aplikacji tego etapu. Stan jest tworzony raz, akcje aktualizują go przez setState, "
                    "a render tylko czyta stan i renderuje właściwy widok."
                ),
                checkpoint=[
                    "Po odświeżeniu strony koszyk nadal ma te same linie.",
                    "Zmiana hash zmienia widok bez przeładowania strony.",
                    "Nie ma drugiego źródła prawdy dla currentView.",
                ],
            ),
            step(
                slug="testy-i-dostepnosc",
                title="Testy, dostępność i granice MVC",
                goal=(
                    "Zabezpiecz funkcje filtrujące testami, sprawdź obsługę klawiatury i dopisz reguły, "
                    "które powstrzymają projekt przed rozjechaniem się."
                ),
                why=(
                    "Projekt staje się realny, gdy ktoś inny może go zmienić bez strachu. Testy funkcji filtrujących "
                    "są tanie, a dostępność jest częścią jakości widoku, nie dodatkiem na koniec."
                ),
                filename="tests/catalog.test.js",
                minutes=60,
                tasks=[
                    "Dodaj testy filtrów, sortowania i koszyka w node:test.",
                    "Sprawdź focus po błędzie formularza i po zmianie widoku.",
                    "Dopisz krótką checklistę granic: model, widok, kontroler.",
                ],
                hints=[
                    "Testuj selectProducts, nie renderCatalog. Widok testuj później w przeglądarce.",
                    "Dla focusu sprawdź document.activeElement, nie tylko wygląd klasy CSS.",
                ],
                answer="""
// tests/catalog.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { filterProducts, sortProducts } from "../src/catalog.js";
import { addToCart, setQuantity } from "../src/cart.js";
import { createInitialState } from "../src/store.js";

const products = [
  { id: "a", name: "Latte", category: "coffee", price: 1599 },
  { id: "b", name: "Grinder", category: "gear", price: 18900 },
];

test("filters by category and query", () => {
  const state = { currentCategory: "coffee", currentQuery: "lat" };
  assert.deepEqual(filterProducts(products, state).map((p) => p.id), ["a"]);
});

test("sorts by price without mutating input", () => {
  const sorted = sortProducts(products, { key: "price", direction: "asc" });
  assert.deepEqual(sorted.map((p) => p.id), ["a", "b"]);
  assert.equal(products[0].id, "a");
});

test("adds the same product as one line with quantity 2", () => {
  const state = { ...createInitialState(), cart: [] };
  const once = addToCart(state, products[0]);
  const twice = addToCart(once, products[0]);
  assert.equal(twice.cart.length, 1);
  assert.equal(twice.cart[0].quantity, 2);
});

test("quantity zero removes the line", () => {
  const state = { ...createInitialState(), cart: [{ productId: "a", quantity: 2 }] };
  assert.deepEqual(setQuantity(state, "a", 0).cart, []);
});

// Accessibility checklist:
// 1. Every control is reachable by Tab and has a visible focus ring.
// 2. Quantity inputs have an accessible name with the product name.
// 3. After validation, focus moves to the first invalid field.
// 4. The cart summary uses role="status" or aria-live="polite".
""",
                explain=(
                    "To jest pełny zestaw testów tego kroku. Nie testuje wyglądu — testuje reguły, "
                    "które najczęściej się psują przy refaktorze."
                ),
                checkpoint=[
                    "Testy przechodzą bez przeglądarki.",
                    "Zmiana kolejności filtrów nie zmienia danych wejściowych.",
                    "Potrafisz wskazać, które pliki są modelem, widokiem i kontrolerem.",
                ],
            ),
        ],
    },
    {
        "slug": "movie-hub",
        "title": "Movie HUB",
        "subtitle": "Wyszukiwarka filmów, szczegóły, lista do obejrzenia i pamięć podręczna — MVC z prawdziwym API.",
        "eyebrow": "Projekt 02 · media",
        "glyph": "02",
        "accent": "#22d3ee",
        "preview": "js_academy/movie-preview.png",
        "level": "średni",
        "duration": "8–10 godzin",
        "stack": ["Vanilla JS", "MVC", "Fetch API", "AbortController"],
        "summary": (
            "Zbudujesz Movie HUB: wyszukiwanie z opóźnieniem, szczegóły filmu, listę do obejrzenia, "
            "oceny i pamięć podręczna, która nie pokazuje starego wyniku po szybkim pisaniu."
        ),
        "outcome": (
            "Po ośmiu krokach umiesz odciąć UI od API, obsłużyć wyścig zapytań i zbudować "
            "aplikację, która ma sensowny stan ładowania, błędu i pustki."
        ),
        "features": [
            "wyszukiwanie filmów z opóźnieniem",
            "filtry gatunku i sortowanie",
            "szczegóły filmu bez przeładowania strony",
            "lista do obejrzenia i oceny w localStorage",
            "pamięć podręczna z czasem życia i anulowanie zapytań",
            "stany loading/error/empty i dostępność",
        ],
        "constraints": [
            "Bez frameworka; jeden stan i czyste funkcje filtrujące.",
            "API jest ukryte za warstwą, więc możesz podmienić je na dane testowe.",
            "Żadnego innerHTML z danymi z API.",
            "Szybkie pisanie nie może podmienić nowszego wyniku starszym.",
        ],
        "files": [
            "index.html",
            "src/movies.js",
            "src/api.js",
            "src/store.js",
            "src/search-controller.js",
            "src/movie-view.js",
            "src/library-store.js",
            "src/movie-cache.js",
            "src/app.js",
            "tests/movies.test.js",
        ],
        "shell": """<!doctype html>
<html lang="pl">
  <head>
    <meta charset="utf-8">
    <meta
      name="viewport"
      content="width=device-width, initial-scale=1"
    >
    <title>Movie HUB</title>
  </head>
  <body>
    <header>
      <h1>Movie HUB</h1>
      <a href="#/watchlist">Lista do obejrzenia</a>
    </header>
    <main data-app></main>
    <script
      type="module"
      src="./src/app.js"
    ></script>
  </body>
</html>""",
        "brief": (
            "Movie HUB wygląda jak prosty klient API, ale uczy trzech trudnych rzeczy: "
            "wyścigu zapytań, trwałego stanu i widoku szczegółów, który nie gubi focusu. "
            "To projekt o przewidywalności, nie o liczbie ekranów."
        ),
        "steps": [
            step(
                slug="model-filmu",
                title="Model filmu i czyste funkcje filtrujące",
                goal=(
                    "Znormalizuj dane z API do jednego kształtu i zdefiniuj filtrowanie, "
                    "sortowanie oraz listę do obejrzenia bez zależności od DOM."
                ),
                why=(
                    "API zmienia nazwy pól, dodaje null i zwraca różne formaty. Jeden normalizer "
                    "sprawia, że reszta aplikacji nie zna tych różnic."
                ),
                filename="src/movies.js",
                minutes=45,
                tasks=[
                    "Napisz normalizeMovie z bezpiecznymi domyślnymi wartościami.",
                    "Dodaj filterMovies i sortMovies jako funkcje czyste.",
                    "Zdefiniuj toggleWatchlist bez mutowania wejściowej tablicy.",
                ],
                hints=[
                    "Nie zakładaj, że genre to tablica. API może zwrócić string, null albo brak pola.",
                    "Oceny trzymaj jako number w zakresie 0–10; formatowanie zostaw widokowi.",
                ],
                answer="""
// src/movies.js
export function normalizeMovie(raw) {
  const genres = Array.isArray(raw.genres)
    ? raw.genres
    : String(raw.genre ?? "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

  return {
    id: String(raw.id),
    title: String(raw.title ?? "Untitled"),
    year: Number(raw.year) || null,
    rating: Math.min(10, Math.max(0, Number(raw.rating) || 0)),
    genres,
    overview: String(raw.overview ?? ""),
    poster: String(raw.poster ?? ""),
  };
}

export function filterMovies(movies, state) {
  const query = state.currentQuery.trim().toLowerCase();
  return movies.filter((movie) => {
    const genreOk =
      state.currentGenre === "all" || movie.genres.includes(state.currentGenre);
    const queryOk =
      !query ||
      `${movie.title} ${movie.overview}`.toLowerCase().includes(query);
    return genreOk && queryOk;
  });
}

export function sortMovies(movies, sort) {
  const direction = sort.direction === "desc" ? -1 : 1;
  return [...movies].sort((a, b) => {
    if (sort.key === "rating") return (a.rating - b.rating) * direction;
    if (sort.key === "year") return ((a.year ?? 0) - (b.year ?? 0)) * direction;
    return a.title.localeCompare(b.title, "pl") * direction;
  });
}

export function toggleWatchlist(ids, movieId) {
  return ids.includes(movieId)
    ? ids.filter((id) => id !== movieId)
    : [...ids, movieId];
}
""",
                explain=(
                    "To jest pełny model tego kroku. Normalizer jest jedynym miejscem, które wie, "
                    "jak wyglądają surowe dane; funkcje filtrujące pracują już na przewidywalnym kształcie."
                ),
                checkpoint=[
                    "normalizeMovie({}) nie rzuca wyjątkiem.",
                    "sortMovies nie mutuje tablicy wejściowej.",
                    "toggleWatchlist dodaje i usuwa to samo id.",
                ],
            ),
            step(
                slug="warstwa-api",
                title="Warstwa API z limitem czasu",
                goal=(
                    "Ukryj fetch za małą warstwą, która normalizuje dane i pilnuje limitu czasu. "
                    "Widok ma dostawać filmy albo błąd, nie surowe response."
                ),
                why=(
                    "Każde wywołanie API może się zawiesić. AbortController i timeout to nie drobiazg; "
                    "bez nich użytkownik patrzy na spinner bez końca."
                ),
                filename="src/api.js",
                minutes=60,
                tasks=[
                    "Zbuduj createMovieApi({ baseUrl, fetchImpl }).",
                    "Dodaj AbortController i limit czasu dla każdego zapytania.",
                    "Normalizuj wynik i zamień błędy HTTP na czytelne komunikaty.",
                ],
                hints=[
                    "Timeout czyść w finally, inaczej zostaje timer po sukcesie.",
                    "Nie rzucaj surowego błędu fetch; opakuj go w MovieApiError z komunikatem dla UI.",
                ],
                answer="""
// src/api.js
import { normalizeMovie } from "./movies.js";

export class MovieApiError extends Error {
  constructor(message, cause) {
    super(message);
    this.name = "MovieApiError";
    this.cause = cause;
  }
}

export function createMovieApi({
  baseUrl = "/api",
  fetchImpl = fetch,
  timeoutMs = 8000,
} = {}) {
  async function request(path, options = {}) {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetchImpl(`${baseUrl}${path}`, {
        ...options,
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new MovieApiError(`API returned ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      if (error.name === "AbortError") {
        throw new MovieApiError("Request timed out. Try again.");
      }
      if (error instanceof MovieApiError) throw error;
      throw new MovieApiError("Could not reach the movie service.", error);
    } finally {
      window.clearTimeout(timer);
    }
  }

  return {
    async search(query, page = 1) {
      const data = await request(
        `/movies?q=${encodeURIComponent(query)}&page=${page}`
      );
      return {
        items: (data.results ?? []).map(normalizeMovie),
        page: Number(data.page) || page,
        totalPages: Number(data.total_pages) || 1,
      };
    },
    async get(id) {
      return normalizeMovie(await request(`/movies/${encodeURIComponent(id)}`));
    },
  };
}
""",
                explain=(
                    "To jest pełna warstwa API. Reszta aplikacji nie wie, czy dane przyszły z sieci, "
                    "z pamięci podręcznej czy z danych testowych — dostaje ten sam kształt."
                ),
                checkpoint=[
                    "Po timeout pojawia się MovieApiError, nie wieczny spinner.",
                    "Widok nie wywołuje fetch bezpośrednio.",
                    "Nieudane zapytanie nie zostawia aktywnego timera.",
                ],
            ),
            step(
                slug="stan-i-router",
                title="Stan i router bez frameworka",
                goal=(
                    "Dodaj widoki start, wyszukiwanie, film i lista do obejrzenia do jednego stanu. "
                    "Adres URL ma być źródłem prawdy dla aktualnego widoku i id filmu."
                ),
                why=(
                    "Bez routera szczegóły filmu są modalem, którego nie da się wysłać linkiem. "
                    "Hash router jest mały, a uczy dokładnie tego samego rozdzielenia co React Router."
                ),
                filename="src/store.js",
                minutes=50,
                tasks=[
                    "Zdefiniuj createInitialState z currentView, currentQuery i selectedMovieId.",
                    "Napisz parseRoute dla #/, #/szukaj i #/film/:id.",
                    "Dodaj updateState, które resetuje stronę przy zmianie query.",
                ],
                hints=[
                    "selectedMovieId nie jest tym samym co film w pamięci podręcznej. Trzymaj id i pobieraj dane osobno.",
                    "Nie parsuj route w widoku. Router należy do warstwy stanu/kontrolera.",
                ],
                answer="""
// src/store.js
export function createInitialState() {
  return {
    currentView: "home",
    currentQuery: "",
    currentGenre: "all",
    currentSort: { key: "rating", direction: "desc" },
    selectedMovieId: null,
    watchlist: [],
    status: "idle",
    error: "",
  };
}

export function updateState(state, patch) {
  const next = { ...state, ...patch };
  if ("currentQuery" in patch) next.currentPage = 1;
  return next;
}

export function parseRoute(hash = window.location.hash) {
  const path = hash.replace(/^#/, "") || "/";
  const movieMatch = path.match(/^\\/film\\/([^/]+)$/);
  if (movieMatch) {
    return { view: "movie", movieId: decodeURIComponent(movieMatch[1]) };
  }
  if (path === "/szukaj") return { view: "search" };
  if (path === "/watchlist") return { view: "watchlist" };
  return { view: "home" };
}

export function toHash(view, movieId = null) {
  if (view === "movie" && movieId) return `#/film/${encodeURIComponent(movieId)}`;
  if (view === "search") return "#/szukaj";
  if (view === "watchlist") return "#/watchlist";
  return "#/";
}
""",
                explain=(
                    "To jest pełny router i stan tego kroku. currentView opisuje ekran, a selectedMovieId "
                    "opisuje dane, które trzeba pobrać — to dwie różne odpowiedzialności."
                ),
                checkpoint=[
                    "Wejście na #/film/tt0133093 ustawia widok movie i id.",
                    "Nieznany hash wraca do home.",
                    "Zmiana query resetuje stronę wyników.",
                ],
            ),
            step(
                slug="wyszukiwanie-z-opoznieniem",
                title="Wyszukiwanie z opóźnieniem i anulowaniem",
                goal=(
                    "Nie wysyłaj zapytania na każdą literę. Anuluj stare zapytanie i ignoruj "
                    "odpowiedź, która przyszła po nowszej."
                ),
                why=(
                    "To klasyczny wyścig: użytkownik pisze „aliens”, a odpowiedź na „ali” wraca ostatnia "
                    "i podmienia wyniki. Samo opóźnienie nie wystarczy; potrzebny jest jeszcze numer requestu lub AbortController."
                ),
                filename="src/search-controller.js",
                minutes=70,
                tasks=[
                    "Zbuduj createSearchController z timerem i AbortController.",
                    "Dodaj numer zapytania, żeby odrzucić spóźnione odpowiedzi.",
                    "Podłącz stany loading, error i empty do widoku.",
                ],
                hints=[
                    "Anuluj poprzednie zapytanie przed nowym, ale i tak sprawdź numer — przerwanie nie zawsze działa natychmiast.",
                    "Opóźnienie 250–350 ms to dobry start; nie ukrywaj stanu ładowania bez końca.",
                ],
                answer="""
// src/search-controller.js
export function createSearchController({
  api,
  onResults,
  onError,
  onLoading,
  delay = 300,
}) {
  let timer = null;
  let controller = null;
  let requestId = 0;

  async function run(query) {
    requestId += 1;
    const currentId = requestId;

    if (controller) controller.abort();
    controller = new AbortController();
    onLoading?.(true);

    try {
      const result = await api.search(query, 1);
      if (currentId !== requestId) return;
      onResults(result);
      onError?.("");
    } catch (error) {
      if (currentId !== requestId) return;
      onError?.(error.message);
    } finally {
      if (currentId === requestId) onLoading?.(false);
    }
  }

  return {
    change(query) {
      window.clearTimeout(timer);
      const trimmed = query.trim();
      if (!trimmed) {
        requestId += 1;
        onResults({ items: [], page: 1, totalPages: 1 });
        onLoading?.(false);
        return;
      }
      timer = window.setTimeout(() => run(trimmed), delay);
    },
    cancel() {
      window.clearTimeout(timer);
      if (controller) controller.abort();
      requestId += 1;
    },
  };
}
""",
                explain=(
                    "To jest pełny kontroler wyszukiwania. Debounce ogranicza liczbę requestów, "
                    "a requestId gwarantuje, że starsza odpowiedź nie wygra z nowszą."
                ),
                checkpoint=[
                    "Szybkie wpisanie pięciu liter nie wysyła pięciu requestów.",
                    "Spóźniona odpowiedź nie podmienia nowszych wyników.",
                    "Puste query czyści wyniki bez requestu.",
                ],
            ),
            step(
                slug="widok-katalogu",
                title="Widok katalogu i szczegółów",
                goal=(
                    "Zbuduj siatkę filmów, filtry i widok szczegółów bez innerHTML. "
                    "Zadbaj o focus i sensowne komunikaty dla czytników ekranu."
                ),
                why=(
                    "Karty z API mogą zawierać dziwne znaki i brak plakatu. Widok musi być odporny, "
                    "a przejście do szczegółów nie może zostawić focusu na usuniętym elemencie."
                ),
                filename="src/movie-view.js",
                minutes=80,
                tasks=[
                    "Napisz renderMovieGrid z kartami i pustym stanem.",
                    "Dodaj renderMovieDetail z obsługą braku plakatu.",
                    "Przenieś focus na nagłówek po zmianie widoku.",
                ],
                hints=[
                    "Plakat to obraz dekoracyjny, jeśli tytuł jest obok; użyj alt=\"\" i opisz film tekstem.",
                    "Przy braku plakatu nie zostawiaj pustego img — pokaż tekstowy placeholder.",
                ],
                answer="""
// src/movie-view.js
import { filterMovies, sortMovies } from "./movies.js";

export function renderMovieGrid(root, movies, state, actions) {
  const visible = sortMovies(filterMovies(movies, state), state.currentSort);

  const toolbar = document.createElement("div");
  toolbar.className = "movie-toolbar";

  const search = document.createElement("input");
  search.type = "search";
  search.placeholder = "Szukaj filmu…";
  search.value = state.currentQuery;
  search.setAttribute("aria-label", "Szukaj filmu");
  search.addEventListener("input", (event) => actions.onQuery(event.target.value));
  toolbar.append(search);

  if (!visible.length) {
    const empty = document.createElement("p");
    empty.setAttribute("role", "status");
    empty.textContent = "Brak filmów. Zmień frazę albo gatunek.";
    root.replaceChildren(toolbar, empty);
    return;
  }

  const grid = document.createElement("div");
  grid.className = "movie-grid";

  for (const movie of visible) {
    const card = document.createElement("article");
    card.className = "movie-card";

    if (movie.poster) {
      const img = document.createElement("img");
      img.src = movie.poster;
      img.alt = "";
      img.loading = "lazy";
      card.append(img);
    }

    const title = document.createElement("h3");
    title.textContent = movie.title;

    const meta = document.createElement("p");
    meta.textContent = `${movie.year ?? "—"} · ${movie.rating.toFixed(1)}/10`;

    const open = document.createElement("button");
    open.type = "button";
    open.textContent = "Szczegóły";
    open.addEventListener("click", () => actions.onOpen(movie.id));

    card.append(title, meta, open);
    grid.append(card);
  }

  root.replaceChildren(toolbar, grid);
}

export function renderMovieDetail(root, movie, isSaved, actions) {
  const article = document.createElement("article");
  article.className = "movie-detail";

  const back = document.createElement("button");
  back.type = "button";
  back.textContent = "← Wróć do wyników";
  back.addEventListener("click", actions.onBack);

  const title = document.createElement("h1");
  title.textContent = movie.title;
  title.tabIndex = -1;

  const overview = document.createElement("p");
  overview.textContent = movie.overview || "Brak opisu.";

  const save = document.createElement("button");
  save.type = "button";
  save.textContent = isSaved ? "Usuń z listy do obejrzenia" : "Dodaj do listy do obejrzenia";
  save.addEventListener("click", () => actions.onToggle(movie.id));

  article.append(back, title, overview, save);
  root.replaceChildren(article);
  title.focus();
}
""",
                explain=(
                    "To jest pełny widok katalogu i szczegółów. Focus przenosi się na h1 z tabIndex -1, "
                    "więc czytnik ekranu i klawiatura wiedzą, że zmienił się kontekst."
                ),
                checkpoint=[
                    "Brak plakatu nie psuje karty.",
                    "Po otwarciu szczegółów focus jest na nagłówku.",
                    "Widok nie używa innerHTML.",
                ],
            ),
            step(
                slug="lista-do-obejrzenia-i-oceny",
                title="Lista do obejrzenia, oceny i trwałość",
                goal=(
                    "Zapisz listę do obejrzenia i oceny w localStorage z wersją danych. "
                    "Po odświeżeniu strony użytkownik wraca do tego samego stanu."
                ),
                why=(
                    "localStorage jest współdzielony przez karty i wersje aplikacji. Bez wersji i walidacji "
                    "stary kształt danych potrafi wywrócić cały widok."
                ),
                filename="src/library-store.js",
                minutes=65,
                tasks=[
                    "Zbuduj createLibraryStore z read/write i wersją.",
                    "Dodaj setRating z zakresem 0–10 i usuwanie oceny.",
                    "Podłącz listę do obejrzenia i oceny do szczegółów filmu.",
                ],
                hints=[
                    "Nie zapisuj całej listy filmów w localStorage. Zapisz id, ocenę i timestamp.",
                    "Jeśli storage jest niedostępny, aplikacja ma działać dalej w pamięci.",
                ],
                answer="""
// src/library-store.js
const KEY = "movie-hub-library";
const VERSION = 1;

export function createLibraryStore(storage = window.localStorage) {
  function read() {
    try {
      const raw = storage.getItem(KEY);
      if (!raw) return { watchlist: [], ratings: {} };
      const data = JSON.parse(raw);
      if (data.version !== VERSION) return { watchlist: [], ratings: {} };
      return {
        watchlist: Array.isArray(data.watchlist) ? data.watchlist : [],
        ratings: data.ratings && typeof data.ratings === "object" ? data.ratings : {},
      };
    } catch (_) {
      return { watchlist: [], ratings: {} };
    }
  }

  function write(next) {
    try {
      storage.setItem(KEY, JSON.stringify({ version: VERSION, ...next }));
    } catch (_) {
      // Keep working in memory when storage is disabled or full.
    }
  }

  return {
    read,
    toggleWatchlist(state, movieId) {
      const watchlist = state.watchlist.includes(movieId)
        ? state.watchlist.filter((id) => id !== movieId)
        : [...state.watchlist, movieId];
      const next = { ...state, watchlist };
      write(next);
      return next;
    },
    setRating(state, movieId, rating) {
      const value = Math.min(10, Math.max(0, Number(rating) || 0));
      const next = {
        ...state,
        ratings: { ...state.ratings, [movieId]: value },
      };
      write(next);
      return next;
    },
  };
}
""",
                explain=(
                    "To jest pełny store biblioteki. Zapisuje tylko to, czego nie da się odtworzyć z API: "
                    "wybory użytkownika. Reszta danych może być trzymana w pamięci podręcznej osobno."
                ),
                checkpoint=[
                    "Po reloadzie lista do obejrzenia i oceny nadal są.",
                    "Uszkodzony JSON nie wywala widoku.",
                    "Ocena 12 jest przycinana do 10.",
                ],
            ),
            step(
                slug="pamiec-podreczna-i-bledy",
                title="Pamięć podręczna, błędy i stany brzegowe",
                goal=(
                    "Dodaj pamięć podręczną z czasem życia, ponów request po błędzie i pokaż użytkownikowi, "
                    "co się dzieje, zamiast pustego ekranu."
                ),
                why=(
                    "Dobra aplikacja nie udaje, że sieć zawsze działa. Pamięć podręczna zmniejsza liczbę requestów, "
                    "ale musi mieć limit czasu; inaczej użytkownik widzi nieaktualne dane."
                ),
                filename="src/movie-cache.js",
                minutes=55,
                tasks=[
                    "Napisz createMovieCache(ttlMs).",
                    "Dodaj ponawianie z ograniczeniem i komunikatem błędu.",
                    "Pokaż loading, error i empty w jednym miejscu.",
                ],
                hints=[
                    "Klucz pamięci podręcznej to id filmu, a wartość { movie, savedAt }.",
                    "Ponawianie nie może zapętlić się bez końca; maksymalnie dwa razy.",
                ],
                answer="""
// src/movie-cache.js
export function createMovieCache(ttlMs = 5 * 60 * 1000) {
  const entries = new Map();

  return {
    get(id) {
      const entry = entries.get(id);
      if (!entry) return null;
      if (Date.now() - entry.savedAt > ttlMs) {
        entries.delete(id);
        return null;
      }
      return entry.movie;
    },
    set(movie) {
      entries.set(movie.id, { movie, savedAt: Date.now() });
    },
    clear() {
      entries.clear();
    },
  };
}

export async function withRetry(task, attempts = 2) {
  let lastError;
  for (let attempt = 0; attempt <= attempts; attempt += 1) {
    try {
      return await task();
    } catch (error) {
      lastError = error;
      if (attempt < attempts) {
        await new Promise((resolve) => window.setTimeout(resolve, 350 * (attempt + 1)));
      }
    }
  }
  throw lastError;
}

export function renderStatus(root, status, message = "") {
  const text = {
    loading: "Ładowanie filmów…",
    error: message || "Nie udało się pobrać danych. Spróbuj ponownie.",
    empty: "Brak wyników dla tego zapytania.",
  }[status];

  if (!text) {
    root.replaceChildren();
    return;
  }

  const paragraph = document.createElement("p");
  paragraph.setAttribute("role", status === "error" ? "alert" : "status");
  paragraph.textContent = text;
  root.replaceChildren(paragraph);
}
""",
                explain=(
                    "To jest pełna pamięć podręczna i obsługa statusów tego kroku. Pamięć podręczna jest mała i lokalny; "
                    "nie próbuje być bazą danych. Ponawianie ma limit, więc błąd nie tworzy przepływu."
                ),
                checkpoint=[
                    "Drugie otwarcie tego samego filmu nie wysyła requestu przed upływem czas życia.",
                    "Po czas życia dane są pobierane ponownie.",
                    "Błąd ma role=alert, a loading role=status.",
                ],
            ),
            step(
                slug="montaz-aplikacji",
                title="Montaż Movie HUB",
                goal=(
                    "Połącz API, router, wyszukiwanie, widoki i bibliotekę w jeden przepływ. "
                    "Po tym kroku aplikacja naprawdę działa w przeglądarce."
                ),
                why=(
                    "MVC bez startu aplikacji to zbiór dobrych plików, który nigdy się nie uruchamia. "
                    "Montaż jest celowo nudny: jedno miejsce czyta stan, wybiera widok i podłącza akcje."
                ),
                filename="src/app.js",
                minutes=65,
                tasks=[
                    "Zbuduj app.js z jednym stanem i funkcją render().",
                    "Podłącz routing hash, wyszukiwanie i szczegóły filmu.",
                    "Dodaj stany loading/error i zapis listy do obejrzenia.",
                ],
                hints=[
                    "Nie wywołuj API w render(). Render tylko czyta stan; dane pobieraj w akcjach.",
                    "Po zmianie widoku przenieś focus na h1, ale nie rób tego przy każdym renderze listy.",
                ],
                answer="""
// src/app.js
import { createMovieApi } from "./api.js";
import { createInitialState, updateState, parseRoute, toHash } from "./store.js";
import { createSearchController } from "./search-controller.js";
import { renderMovieGrid, renderMovieDetail } from "./movie-view.js";
import { createLibraryStore } from "./library-store.js";
import { createMovieCache, renderStatus, withRetry } from "./movie-cache.js";

const root = document.querySelector("[data-app]");
const api = createMovieApi();
const cache = createMovieCache();
const library = createLibraryStore();
let movies = [];
let state = { ...createInitialState(), ...library.read() };

function setState(patch) {
  state = updateState(state, patch);
  render();
}

const search = createSearchController({
  api,
  onLoading: (value) => setState({ status: value ? "loading" : "idle" }),
  onError: (message) => setState({ error: message, status: message ? "error" : "idle" }),
  onResults: (result) => {
    movies = result.items;
    setState({ status: result.items.length ? "ready" : "empty" });
  },
});

async function openMovie(id) {
  setState({ status: "loading", selectedMovieId: id, currentView: "movie" });
  try {
    let movie = cache.get(id);
    if (!movie) {
      movie = await withRetry(() => api.get(id));
      cache.set(movie);
    }
    state = { ...state, status: "ready", selectedMovie: movie };
    render();
  } catch (error) {
    setState({ status: "error", error: error.message });
  }
}

function render() {
  root.dataset.view = state.currentView;
  if (state.status === "loading") return renderStatus(root, "loading");
  if (state.status === "error") return renderStatus(root, "error", state.error);

  if (state.currentView === "movie" && state.selectedMovie) {
    const movie = state.selectedMovie;
    renderMovieDetail(root, movie, state.watchlist.includes(movie.id), {
      onBack: () => (window.location.hash = toHash("search")),
      onToggle: (movieId) => {
        state = library.toggleWatchlist(state, movieId);
        render();
      },
    });
    return;
  }

  if (state.currentView === "movie" && state.selectedMovieId) {
    openMovie(state.selectedMovieId);
    return;
  }

  const actions = {
    onOpen: (id) => (window.location.hash = toHash("movie", id)),
    onQuery: (value) => {
      setState({ currentQuery: value, currentView: "search" });
      search.change(value);
    },
  };

  if (state.currentView === "watchlist") {
    const selected = movies.filter((movie) => state.watchlist.includes(movie.id));
    renderMovieGrid(root, selected, state, actions);
    return;
  }

  renderMovieGrid(root, movies, state, actions);
}

function syncRoute() {
  const route = parseRoute();
  state = {
    ...state,
    currentView: route.view,
    selectedMovieId: route.movieId,
    selectedMovie: null,
    status: "idle",
    error: "",
  };
  if (route.view === "movie" && route.movieId) openMovie(route.movieId);
  else render();
}

window.addEventListener("hashchange", syncRoute);
syncRoute();
""",
                explain=(
                    "To jest pełny montaż Movie HUB. Render nie pobiera danych; robi to openMovie. "
                    "Dzięki temu możesz dodać pamięć podręczną, ponawianie i obsługę focusu bez zmiany widoków."
                ),
                checkpoint=[
                    "Aplikacja startuje z jednym stanem i nie tworzy drugiego currentView.",
                    "Wejście na #/film/:id pokazuje szczegóły, a powrót wraca do wyników.",
                    "Błąd API pokazuje komunikat zamiast pustej siatki.",
                ],
            ),
            step(
                slug="testy-i-final",
                title="Testy, dostępność i finalny montaż",
                goal=(
                    "Połącz wszystko w app.js, dopisz testy funkcji filtrujących i przejdź checklistę jakości. "
                    "To moment, w którym projekt staje się portfolio, a nie ćwiczeniem."
                ),
                why=(
                    "Rekruter nie czyta wszystkich linii. Widzi README, testy i to, czy potrafisz "
                    "wyjaśnić decyzje. Ten krok zamienia kod w dowód."
                ),
                filename="tests/movies.test.js",
                minutes=70,
                tasks=[
                    "Dodaj testy normalizacji, filtrów i listy do obejrzenia.",
                    "Sprawdź focus, aria-live i zachowanie przy błędzie API.",
                    "Dopisz README: cel, stack, uruchomienie, decyzje i znane ograniczenia.",
                ],
                hints=[
                    "Test normalizacji z pustym obiektem jest ważniejszy niż test szczęśliwej ścieżki.",
                    "W README opisz wyścig zapytań; to najlepszy dowód, że rozumiesz projekt.",
                ],
                answer="""
// tests/movies.test.js
import test from "node:test";
import assert from "node:assert/strict";
import {
  normalizeMovie,
  filterMovies,
  sortMovies,
  toggleWatchlist,
} from "../src/movies.js";

test("normalizes missing API fields", () => {
  const movie = normalizeMovie({ id: 7 });
  assert.equal(movie.id, "7");
  assert.equal(movie.title, "Untitled");
  assert.deepEqual(movie.genres, []);
  assert.equal(movie.rating, 0);
});

test("filters by genre and query", () => {
  const movies = [
    normalizeMovie({ id: 1, title: "Alien", genres: ["sci-fi"] }),
    normalizeMovie({ id: 2, title: "Heat", genres: ["crime"] }),
  ];
  const result = filterMovies(movies, {
    currentGenre: "sci-fi",
    currentQuery: "ali",
  });
  assert.deepEqual(result.map((m) => m.id), ["1"]);
});

test("sorts by rating descending without mutation", () => {
  const movies = [
    normalizeMovie({ id: 1, title: "A", rating: 6 }),
    normalizeMovie({ id: 2, title: "B", rating: 9 }),
  ];
  const sorted = sortMovies(movies, { key: "rating", direction: "desc" });
  assert.deepEqual(sorted.map((m) => m.id), ["2", "1"]);
  assert.equal(movies[0].id, "1");
});

test("toggles watchlist ids", () => {
  assert.deepEqual(toggleWatchlist([], "7"), ["7"]);
  assert.deepEqual(toggleWatchlist(["7"], "7"), []);
});

// Portfolio README checklist:
// - What problem does Movie HUB solve?
// - How does the request race get prevented?
// - Where is the MVC boundary?
// - How to run tests and the app?
// - What would you add next, and why?
""",
                explain=(
                    "To jest pełny zestaw testów końcowych. Po tym kroku masz działającą aplikację, "
                    "testy reguł i historię decyzji, którą możesz pokazać w portfolio."
                ),
                checkpoint=[
                    "Testy przechodzą bez sieci.",
                    "README wyjaśnia wyścig zapytań i granice MVC.",
                    "Potrafisz wskazać trzy rzeczy, które dodałbyś w wersji 2.",
                ],
            ),
        ],
    },
]


def get_project(slug: str) -> dict | None:
    return next((project for project in PROJECTS if project["slug"] == slug), None)


def get_step(project: dict, step_slug: str) -> dict | None:
    return next((step for step in project["steps"] if step["slug"] == step_slug), None)


def all_steps(project: dict) -> list[dict]:
    return project["steps"]
