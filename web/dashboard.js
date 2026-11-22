// Patient dashboard for a laptop (synthetic data). Search-first: suggestions appear as you type and the page
// never lists every patient. The sidebar filters by tag or village. "Must review" holds what the ANM has to see.
// Nothing here diagnoses: danger flags only say "Refer to PHC", trend chips only Higher / Lower / Same.
"use strict";

(() => {
  const $ = selector => document.querySelector(selector);
  const input = $("#q");
  const clear = $("#q-clear");
  const list = $("#suggest");
  const nav = $("#nav");
  const crumbs = $("#crumbs");
  const view = $("#view");
  const langSelect = $("#speech-language");
  const MAX_SUGGESTIONS = 6;
  const MAX_RECENT = 4;
  const MAX_DUE = 6;
  const LEAVE_MS = 220;
  const RECENT_KEY = "dashboard-recent";
  const LANG_KEY = "dashboard-lang";
  const FILTERS_KEY = "dashboard-filters-open";

  const TAGS = [["due_today", "Due today"], ["overdue", "Overdue"], ["danger", "Danger sign"],
    ["not_asked", "Not asked"], ["needs_review", "Needs review"]];
  const STEPS = [["flagged", "Flagged"], ["referred", "Referred"], ["reached_phc", "Reached PHC"], ["closed", "Closed"]];
  const STEP_ACTION = { referred: "Mark referred", reached_phc: "Mark reached PHC", closed: "Mark closed" };
  const TYPES = { anc: "Antenatal", pnc: "Postnatal", hbnc: "Newborn", hbyc: "Young child" };
  const FIELDS = { gestational_month: "Pregnancy month", gestational_trimester: "Pregnancy trimester",
    weight_kg: "Weight", hb: "Hb", bp: "BP",
    temperature: "Temperature", breaths_per_min: "Breathing", next_visit_date: "Next visit",
    ifa_taking: "IFA tablets", vaccinations_given: "Vaccines given", vaccinations_due: "Vaccines due",
    medicines_given: "Medicines already given" };
  const AUDIT = { flag: "Danger flag", concern_noted: "Concern noted", concern_flagged: "Concern flagged for ANM",
    visit_switch: "Visit type changed", saved: "Saved", undone: "Undone", referral_referred: "Referred",
    referral_reached_phc: "Reached PHC", referral_closed: "Closed" };
  const BY = { anm: "ANM", rules: "Rules check", llm: "AI check", asha: "ASHA", voice: "Voice", screen: "Screen" };
  const DUE_ORDER = { overdue: 0, today: 1, soon: 2, later: 3, unknown: 4 };

  // 24px line icons (stroke only; styled by dashboard.css)
  const ICONS = {
    home: '<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z"/>',
    review: '<path d="M9 4h6v3H9z"/><path d="M15 5h2a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h2"/><path d="m9 13 2 2 4-4"/>',
    flag: '<path d="M5 21V4"/><path d="M5 4h11l-2 4 2 4H5"/>',
    calendar: '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
    clock: '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
    tag: '<path d="M4 12V5a1 1 0 0 1 1-1h7l8 8-8 8z"/><circle cx="8.5" cy="8.5" r="1.3"/>',
    place: '<path d="M12 21s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    ask: '<circle cx="12" cy="12" r="8"/><path d="M9.6 9.5a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5v.4M12 17h.01"/>',
    trend: '<path d="M4 17l5-5 4 3 7-8"/><path d="M15 7h5v5"/>',
    list: '<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
    back: '<path d="M15 6l-6 6 6 6"/>',
    filter: '<path d="M4 6h16M7 12h10M10 18h4"/>',
    chevron: '<path d="m6 9 6 6 6-6"/>',
    print: '<path d="M7 9V3h10v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 14h10v7H7z"/>',
  };

  let board = null;          // /api/dashboard
  let patient = null;        // /api/patients/{id}
  let tab = "report";
  let navAt = "overview";    // which sidebar item is current
  let filtersOpen = false;   // set from storage once `store` exists
  let active = -1;
  let shown = [];            // suggestions on screen
  let loadToken = 0;
  let lastBoard = "";        // raw JSON on screen, to spot new data
  let lastPatient = "";

  // ---------- small helpers ----------

  function el(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (value == null || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    }
    node.append(...children.flat().filter(child => child != null && child !== false));
    return node;
  }
  const raw = (tag, text, cls) => el(tag, { class: cls, "data-no-i18n": true, text });
  function icon(name) {
    const span = el("span", { class: "d-ico", "aria-hidden": "true" });
    span.innerHTML = `<svg viewBox="0 0 24 24">${ICONS[name]}</svg>`;
    return span.firstChild;
  }
  const store = {
    get(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode */ } },
  };
  filtersOpen = store.get(FILTERS_KEY, false) === true;
  const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
  const lang = () => window.I18n?.lang() || langSelect.value || "en";
  const locale = () => window.I18n?.locale() || "en-IN";
  const signName = (sign, fallback) => board?.sign_names?.[sign]?.[lang()] || patient?.sign_names?.[sign]?.[lang()]
    || fallback || sign;
  const relationLabel = relation => ({ mother: "Mother", husband: "Husband" })[relation] || relation;
  const fold = text => String(text ?? "").toLocaleLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");
  const tagLabel = key => TAGS.find(([k]) => k === key)?.[1] || key;
  const initials = name => String(name).split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join("").toUpperCase();

  function shortDate(iso) {
    if (!iso) return "";
    const date = new Date(`${iso.slice(0, 10)}T00:00:00`);
    return new Intl.DateTimeFormat(locale(), { day: "numeric", month: "short" }).format(date);
  }

  function format(field, value) {
    if (field === "weight_kg") return `${value} kg`;
    if (field === "hb") return `${value} g/dL`;
    if (field === "breaths_per_min") return `${value} / min`;
    if (field === "bp") return value.join("/");
    if (field === "temperature") return `${value[0]} °${value[1]}`;
    if (field === "next_visit_date") return shortDate(value);
    if (typeof value === "boolean") return value ? "Taking" : "Not taking";
    if (field === "medicines_given") return value.map(m =>
      `${m.name}${m.count ? ` × ${m.count}` : ""}${m.by ? ` (by ${m.by})` : ""}`).join(", ");
    return Array.isArray(value) ? value.join(", ") : String(value);
  }

  function dueText(due) {
    if (!due || due.state === "unknown") return "No visit date yet";
    if (due.state === "today") return "Due today";
    if (due.state === "overdue") return due.days === -1 ? "Overdue by 1 day" : `Overdue by ${-due.days} days`;
    return due.days === 1 ? "Due in 1 day" : `Due in ${due.days} days`;
  }

  async function send(url, body) {
    const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body) });
    if (!response.ok) throw new Error(`${url} answered ${response.status}`);
    return response.json();
  }

  // ---------- routing: ?patient= | ?tag= | ?village= | ?q= ----------

  const params = () => new URLSearchParams(location.search);
  function go(next, replace = false) {
    const url = new URL(location.href);
    url.search = new URLSearchParams(Object.entries(next).filter(([, v]) => v)).toString();
    url.hash = "";
    history[replace ? "replaceState" : "pushState"](null, "", url);
    route();
  }

  function route() {
    closeSuggest();
    const p = params();
    const id = p.get("patient");
    const tag = p.get("tag"), village = p.get("village"), query = p.get("q");
    if (tag) filtersOpen = true;
    navAt = id || query ? null : tag ? `tag:${tag}` : village ? `village:${village}` : navAt?.startsWith("#") ? navAt : "overview";
    drawNav();
    if (id) return openPatient(id);
    patient = null;
    if (tag || village || query) return drawResults({ tag, village, query });
    drawHome();
  }

  async function loadBoard() {
    lastBoard = await fetchText("/api/dashboard");
    board = JSON.parse(lastBoard);
  }

  async function fetchText(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`${url} answered ${response.status}`);
    return response.text();
  }

  function scrollToSection(id) {
    document.getElementById(id)?.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
  }

  // Overview sections live on the home page: go home, then scroll.
  function openSection(id) {
    navAt = `#${id}`;
    if (location.search) go({}); else { drawNav(); }
    requestAnimationFrame(() => scrollToSection(id));
  }

  // ---------- sidebar and breadcrumb ----------

  function navItem({ key, label, iconName, count, danger, dot, onclick, raw: isRaw, sub }) {
    const current = navAt === key;
    return el("button", { type: "button", class: `d-nav-item ${sub ? "is-sub" : ""}`, "aria-current": current ? "page" : null, onclick },
      iconName ? icon(iconName) : null,
      isRaw ? raw("span", label, "d-nav-label") : el("span", { class: "d-nav-label", text: label }),
      dot ? el("span", { class: "d-nav-dot", title: "Danger sign" }) : null,
      count != null ? el("span", { class: `d-nav-n ${danger && count ? "is-danger" : ""}`, text: String(count) }) : null);
  }

  function navGroup(title, items) {
    return el("div", { class: "d-nav-group" }, el("p", { class: "d-nav-head", text: title }), items);
  }

  // Filters fold away in a drop-down; it opens by itself when a filter is picked from elsewhere.
  let filtersJustToggled = false;
  function filterMenu() {
    const items = el("div", { id: "nav-filters", class: `d-nav-menu ${filtersJustToggled ? "is-opening" : ""}`, hidden: !filtersOpen },
      TAGS.map(([key, label]) => navItem({ key: `tag:${key}`, label, iconName: "tag", sub: true,
        count: board.tags[key] ?? 0, danger: key === "danger", onclick: () => go({ tag: key }) })));
    filtersJustToggled = false;
    const toggle = el("button", { type: "button", class: "d-nav-item d-nav-toggle", "aria-expanded": String(filtersOpen),
      "aria-controls": "nav-filters",
      onclick: () => {
        filtersOpen = !filtersOpen;
        filtersJustToggled = filtersOpen;
        store.set(FILTERS_KEY, filtersOpen);
        drawNav();
      } },
      icon("filter"), el("span", { class: "d-nav-label", text: "Filters" }), icon("chevron"));
    return el("div", { class: "d-nav-group" }, toggle, items);
  }

  function drawNav() {
    if (!board) return nav.replaceChildren();
    const review = board.report.length + board.checks.length;
    nav.replaceChildren(
      navGroup("Today", [
        navItem({ key: "overview", label: "Overview", iconName: "home",
          onclick: () => { navAt = "overview"; go({}); window.scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" }); } }),
        el("div", { class: "d-nav-sub" },
          navItem({ key: "#must", label: "Must review", iconName: "review", count: review, sub: true,
            onclick: () => openSection("must") }),
          navItem({ key: "#flags", label: "Danger flags", iconName: "flag", count: board.flags.length, danger: true, sub: true,
            onclick: () => openSection("flags") }),
          navItem({ key: "#due", label: "Visits due", iconName: "calendar", count: board.tags.due_today + board.tags.overdue,
            sub: true, onclick: () => openSection("due") })),
      ]),
      filterMenu(),
      navGroup("Villages", board.villages.map(v => navItem({ key: `village:${v.village}`, label: v.village, raw: true,
        iconName: "place", dot: v.open_flags > 0, onclick: () => go({ village: v.village }) }))));
  }

  function drawCrumbs(...trail) {
    const items = [["Dashboard", () => { navAt = "overview"; go({}); }], ...trail];
    crumbs.replaceChildren(...items.map(([label, onclick, isRaw], i) => {
      const last = i === items.length - 1;
      const text = isRaw ? raw("span", label) : el("span", { text: label });
      if (last) return el("li", {}, el("span", { "aria-current": "page" }, text));
      return el("li", {}, !onclick ? text
        : el("a", { href: "dashboard.html", onclick: event => { event.preventDefault(); onclick(); } }, text));
    }));
  }

  // ---------- search ----------

  function matches(query) {
    const q = fold(query.trim());
    if (!q) return [];
    const score = (text) => {
      const t = fold(text);
      if (!t.includes(q)) return 0;
      return t.startsWith(q) ? 3 : t.split(/\s+/).some(word => word.startsWith(q)) ? 2 : 1;
    };
    // Her name, ID or the name as spoken in Hindi / Kannada rank above a village or relative's name.
    const people = board.patients.map(p => {
      const own = Math.max(...[p.name, p.id, ...(p.spoken_names || [])].map(score));
      const near = Math.max(score(p.village), score(p.relation_name));
      const via = !own && !score(p.village) && score(p.relation_name) ? "relation" : null;
      return { kind: "patient", item: p, rank: own ? own + 1 : near ? 1 : 0, via };
    }).filter(m => m.rank > 0);
    const villages = [...new Set(board.patients.map(p => p.village))]
      .filter(v => score(v)).map(v => ({ kind: "village", item: v, rank: score(v) + 0.5 }));
    return [...people, ...villages].sort((a, b) => b.rank - a.rank).slice(0, MAX_SUGGESTIONS);
  }

  function highlight(text, query) {
    const at = fold(text).indexOf(fold(query.trim()));
    if (!query.trim() || at < 0) return [raw("span", text)];
    const end = at + query.trim().length;
    return [raw("span", text.slice(0, at)), raw("mark", text.slice(at, end)), raw("span", text.slice(end))];
  }

  function suggestionRow(entry, index, query) {
    const isVillage = entry.kind === "village";
    const p = entry.item;
    const count = isVillage ? board.patients.filter(x => x.village === p).length : 0;
    const meta = isVillage
      ? el("span", { class: "d-s-meta" }, el("span", { text: "Village" }), " · ",
          el("span", { text: count === 1 ? "1 patient" : `${count} patients` }))
      : entry.via === "relation"
        ? el("span", { class: "d-s-meta" }, el("span", { text: relationLabel(p.relation) }), ": ",
            el("span", { class: "d-s-via" }, highlight(p.relation_name, query)))
        : el("span", { class: "d-s-meta" }, raw("span", `ID ${p.id}`), " · ", raw("span", p.village), " · ",
            el("span", { text: TYPES[p.visit_type] || p.visit_type }));
    const mark = el("span", { class: `d-s-icon ${isVillage ? "is-place" : ""}`, "aria-hidden": "true" });
    const flag = !isVillage && p.open_flags ? el("span", { class: "d-dot", title: "Danger sign" }) : null;
    return el("li", { id: `s-${index}`, role: "option", class: "d-s-row", "aria-selected": index === active ? "true" : "false",
      onpointerdown: event => event.preventDefault(), onclick: () => pick(entry) },
      mark, el("span", { class: "d-s-text" }, el("span", { class: "d-s-name" }, highlight(isVillage ? p : p.name, query)), meta), flag);
  }

  function recentRows() {
    const recent = store.get(RECENT_KEY, []).map(id => board.patients.find(p => p.id === id)).filter(Boolean);
    return recent.map(p => ({ kind: "patient", item: p, recent: true }));
  }

  function drawSuggest() {
    if (!board) return;
    const query = input.value;
    clear.hidden = !query;
    shown = query.trim() ? matches(query) : recentRows();
    active = Math.min(active, shown.length - 1);
    const rows = shown.map((entry, i) => suggestionRow(entry, i, query));
    if (!query.trim() && rows.length) rows.unshift(el("li", { class: "d-s-head", role: "presentation", text: "Recent" }));
    if (query.trim() && !shown.length) {
      rows.push(el("li", { class: "d-s-empty", role: "presentation", text: "No patient found. Try a name, ID or village." }));
    }
    list.replaceChildren(...rows);
    const open = rows.length > 0 && document.activeElement === input;
    list.hidden = !open;
    input.setAttribute("aria-expanded", String(open));
    if (active >= 0) input.setAttribute("aria-activedescendant", `s-${active}`);
    else input.removeAttribute("aria-activedescendant");
  }

  function closeSuggest() {
    list.hidden = true;
    active = -1;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  }

  function remember(id) {
    store.set(RECENT_KEY, [id, ...store.get(RECENT_KEY, []).filter(x => x !== id)].slice(0, MAX_RECENT));
  }

  function openPatientPage(id) {
    remember(id);
    go({ patient: id });
  }

  function pick(entry) {
    input.value = "";
    clear.hidden = true;
    input.blur();
    if (entry.kind === "village") return go({ village: entry.item });
    openPatientPage(entry.item.id);
  }

  input.addEventListener("input", () => { active = -1; drawSuggest(); });
  input.addEventListener("focus", drawSuggest);
  input.addEventListener("blur", () => setTimeout(closeSuggest, 0));
  input.addEventListener("keydown", event => {
    const count = shown.length;
    if (event.key === "ArrowDown" && count) { active = (active + 1) % count; drawSuggest(); event.preventDefault(); }
    else if (event.key === "ArrowUp" && count) { active = (active - 1 + count) % count; drawSuggest(); event.preventDefault(); }
    else if (event.key === "Enter") {
      event.preventDefault();
      if (active >= 0 && shown[active]) return pick(shown[active]);
      const query = input.value.trim();
      if (query) { input.blur(); go({ q: query }); }
    } else if (event.key === "Escape") {
      if (!list.hidden) closeSuggest();
      else { input.value = ""; clear.hidden = true; input.blur(); }
    }
  });
  clear.addEventListener("click", () => { input.value = ""; input.focus(); drawSuggest(); });

  // "/" jumps to search, as on most search pages
  document.addEventListener("keydown", event => {
    if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.target.closest("input, textarea, select, [contenteditable]")) return;
    event.preventDefault();
    input.focus();
  });

  // ---------- shared pieces ----------

  function panel({ id, title, iconName, count, danger, help, badge, end, cls }, ...body) {
    const titleId = id ? `${id}-title` : null;
    return el("section", { class: `d-panel ${cls || ""}`, id, "aria-labelledby": titleId },
      el("div", { class: "d-panel-head" },
        el("h2", { class: "d-h2", id: titleId }, iconName ? icon(iconName) : null, el("span", { text: title })),
        count != null ? el("span", { class: `d-count ${danger && count ? "is-danger" : ""}`, text: String(count) }) : null,
        badge,
        end ? el("div", { class: "d-head-end" }, end) : null,
        help ? el("p", { class: "d-help", text: help }) : null),
      ...body);
  }

  function patientLink(item) {
    return el("a", { class: "d-who", href: `?patient=${encodeURIComponent(item.patient_id)}`,
      onclick: event => { event.preventDefault(); openPatientPage(item.patient_id); } },
      raw("span", item.patient, "d-who-name"), raw("span", item.village, "d-who-place"));
  }

  const quote = text => (text ? raw("p", `“${text}”`, "c-quote d-quote") : null);
  const when = iso => el("span", { class: "d-when" }, raw("span", shortDate(iso)));
  const empty = text => el("p", { class: "d-empty", text });
  const referLine = (sign, label) => el("p", { class: "d-sign is-danger" }, raw("span", signName(sign, label)), " — ",
    el("span", { text: "Refer to PHC" }));

  async function act(button, request) {
    const card = button.closest(".d-row, tr, .d-flagcard");
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    try {
      await request();
      card?.classList.add("is-leaving");
      await new Promise(resolve => setTimeout(resolve, reducedMotion() ? 0 : LEAVE_MS));
      await loadBoard();
      route();
    } catch (error) {
      console.error(error);
      button.disabled = false;
      button.removeAttribute("aria-busy");
      button.after(el("p", { class: "d-error", role: "alert", text: "Could not save. Try again." }));
    }
  }

  // Flagged → Referred → Reached PHC → Closed. Returns [track, next-step button or null].
  function ladder(flag) {
    const at = STEPS.findIndex(([key]) => key === flag.step);
    const track = el("ol", { class: "d-ladder", "aria-label": "Referral steps" },
      STEPS.map(([key, label], i) => el("li", { class: i < at ? "is-done" : i === at ? "is-now" : "",
        "aria-current": i === at ? "step" : null }, el("span", { class: "d-ladder-dot", "aria-hidden": "true" }),
        el("span", { class: "d-ladder-label", text: label }))));
    const next = STEPS[at + 1]?.[0];
    const button = next ? el("button", { type: "button", class: "d-btn d-btn-primary",
      onclick: event => {
        const ok = confirm(`Move this flag to “${STEPS[at + 1][1]}”? This cannot be undone.`);
        if (ok) act(event.currentTarget, () => send("/api/referrals", { key: flag.key, step: next }));
      } }, STEP_ACTION[next]) : null;
    return [track, button];
  }

  // One line of the register: serial · who · what · when + action
  function row(item, what, button, withPatient) {
    return el("li", { class: "d-row" },
      withPatient ? patientLink(item) : el("span", { class: "d-when" }, raw("span", shortDate(item.at))),
      el("div", { class: "d-row-what" }, what),
      el("div", { class: "d-row-end" }, withPatient ? when(item.at) : null, button));
  }

  function reportRow(item, withPatient = true) {
    const isFlag = item.key.startsWith("flag:");
    const what = [isFlag ? referLine(item.sign, item.label) : el("p", { class: "d-sign is-concern", text: "ASHA concern" }),
      quote(item.quote)];
    const button = el("button", { type: "button", class: "d-btn", onclick: event => act(event.currentTarget,
      () => send("/api/review-marks", { key: item.key, kind: "reported" })) }, "Mark reported to ANM");
    return row(item, what, button, withPatient);
  }

  function checkRow(item, withPatient = true) {
    const what = item.kind === "odd_value"
      ? [el("p", { class: "d-sign is-check" }, el("span", { text: FIELDS[item.field] || item.field }), ": ",
          raw("span", format(item.field, item.value))), el("p", { class: "d-help", text: "This reading looks unusual. Check it with her." })]
      : [el("p", { class: "d-sign is-check" }, raw("span", signName(item.sign, item.label))),
          el("p", { class: "d-help", text: "Answers differ. Ask again." }), quote(item.quote)];
    const button = el("button", { type: "button", class: "d-btn", onclick: event => act(event.currentTarget,
      () => send("/api/review-marks", { key: item.key, kind: "checked" })) }, "Mark checked");
    return row(item, what, button, withPatient);
  }

  function dueBadge(due) {
    return el("span", { class: `d-due is-${due.state}`, text: dueText(due) });
  }

  const byDue = (a, b) => (DUE_ORDER[a.due.state] - DUE_ORDER[b.due.state]) || (a.due.days ?? 0) - (b.due.days ?? 0);

  // ---------- home ----------

  function hero() {
    const today = new Date(`${board.today}T00:00:00`);
    const day = new Intl.DateTimeFormat(locale(), { weekday: "long", day: "numeric", month: "long" }).format(today);
    return el("header", { class: "d-hero" },
      el("div", {},
        el("p", { class: "d-hero-kicker", text: "Supervisor view" }),
        el("h1", { text: "Patient dashboard" }),
        el("p", { class: "d-hero-sub", text: "See who needs a referral, what to report to the ANM, and who is due for a visit." })),
      el("p", { class: "d-hero-date" }, raw("span", day, "d-hero-day"), raw("span", String(today.getFullYear()), "d-hero-year")));
  }

  function stat({ label, n, sub, iconName, cls, onclick }) {
    return el("button", { type: "button", class: `d-stat ${cls || ""} ${n ? "" : "is-zero"}`, onclick },
      el("span", { class: "d-stat-label", text: label }),
      el("span", { class: "d-stat-icon" }, icon(iconName)),
      raw("span", String(n), "d-stat-n"),
      el("span", { class: "d-stat-sub", text: sub }));
  }

  function stats() {
    return el("div", { class: "d-stats" },
      stat({ label: "Open danger flags", n: board.flags.length, sub: "Refer to PHC, then follow up", iconName: "flag",
        cls: "is-danger", onclick: () => openSection("flags") }),
      stat({ label: "Must review", n: board.report.length + board.checks.length, sub: "To report or double-check",
        iconName: "review", cls: "is-review", onclick: () => openSection("must") }),
      stat({ label: "Due today", n: board.tags.due_today, sub: "Visit planned for today", iconName: "calendar",
        onclick: () => go({ tag: "due_today" }) }),
      stat({ label: "Overdue", n: board.tags.overdue, sub: "Past the visit date", iconName: "clock", cls: "is-overdue",
        onclick: () => go({ tag: "overdue" }) }));
  }

  function villageList() {
    return el("ul", { class: "d-villages" }, board.villages.map(v => {
      const share = v.patients ? Math.round((v.visited_30_days / v.patients) * 100) : 0;
      return el("li", {},
        el("button", { type: "button", class: "d-village", onclick: () => go({ village: v.village }) },
          el("span", { class: "d-village-top" }, raw("span", v.village, "d-village-name"),
            v.open_flags ? el("span", { class: "d-tag is-danger" }, raw("span", String(v.open_flags)), " ",
              el("span", { text: v.open_flags === 1 ? "open flag" : "open flags" })) : null),
          el("span", { class: "d-meter", "aria-hidden": "true" }, el("span", { style: `inline-size:${share}%` })),
          el("span", { class: "d-village-meta" },
            el("span", { text: `${v.visited_30_days} of ${v.patients} visited in 30 days` }),
            el("span", { text: v.visits_this_week === 1 ? "1 visit this week" : `${v.visits_this_week} visits this week` }))));
    }));
  }

  function mustReview() {
    const tabs = [["report", "Report to ANM", board.report.length], ["checks", "Double-check", board.checks.length],
      ["villages", "Villages", null]];
    const total = board.report.length + board.checks.length;
    const body = tab === "report"
      ? (board.report.length ? el("ol", { class: "d-rows" }, board.report.map(i => reportRow(i))) : empty("Nothing to report. All caught up."))
      : tab === "checks"
        ? (board.checks.length ? el("ol", { class: "d-rows" }, board.checks.map(i => checkRow(i))) : empty("Nothing to double-check."))
        : villageList();
    const select = key => {
      tab = key;
      $("#must").replaceWith(mustReview());
      $(`#tab-${key}`)?.focus();
    };
    const tablist = el("div", { class: "d-tabs", role: "tablist", "aria-label": "Must review" },
      tabs.map(([key, label, n]) => el("button", { type: "button", role: "tab", id: `tab-${key}`,
        "aria-selected": String(tab === key), "aria-controls": "must-panel", tabindex: tab === key ? "0" : "-1",
        onclick: () => select(key),
        onkeydown: event => {
          const i = tabs.findIndex(([k]) => k === key);
          const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
          if (step) select(tabs[(i + step + tabs.length) % tabs.length][0]);
        } },
        el("span", { text: label }), n != null ? el("span", { class: "d-tab-n", text: String(n) }) : null)));
    const waiting = total ? el("span", { class: "d-must-n" }, raw("span", String(total)), " ",
      el("span", { text: total === 1 ? "item waiting" : "items waiting" })) : null;
    return panel({ id: "must", title: "Must review", iconName: "review", cls: `d-must ${total ? "has-items" : ""}`,
      badge: waiting, end: tablist },
      el("div", { id: "must-panel", role: "tabpanel", "aria-labelledby": `tab-${tab}`, class: "d-tabpanel" }, body));
  }

  function visitsDue() {
    const due = board.patients.filter(p => ["overdue", "today", "soon"].includes(p.due.state)).sort(byDue);
    const more = due.length > MAX_DUE;
    return panel({ id: "due", title: "Visits due", iconName: "calendar", count: due.length },
      due.length
        ? el("ul", { class: "d-due-list" }, due.slice(0, MAX_DUE).map(p => el("li", {},
            el("a", { class: "d-due-row", href: `?patient=${encodeURIComponent(p.id)}`,
              onclick: event => { event.preventDefault(); openPatientPage(p.id); } },
              el("span", { class: "d-who" }, raw("span", p.name, "d-who-name"), raw("span", p.village, "d-who-place")),
              dueBadge(p.due)))))
        : empty("No one is due this week."),
      board.tags.overdue || more
        ? el("div", { class: "d-due-more" }, el("button", { type: "button", class: "d-link",
            onclick: () => go({ tag: board.tags.overdue ? "overdue" : "due_today" }) },
            el("span", { text: "See all" }), " →"))
        : null);
  }

  function flagTable(flags) {
    return el("table", { class: "d-table is-register" },
      el("thead", {}, el("tr", {},
        el("th", { class: "d-n" }, el("span", { class: "d-sr", text: "Number" })),
        el("th", { class: "d-col-who", text: "Patient" }), el("th", { class: "d-col-sign", text: "Danger sign" }),
        el("th", { text: "ASHA said" }), el("th", { class: "d-col-step", text: "Referral track" }),
        el("th", { class: "d-col-act", text: "Next step" }))),
      el("tbody", {}, flags.map((flag, i) => {
        const [track, button] = ladder(flag);
        return el("tr", {},
          raw("td", String(i + 1).padStart(2, "0"), "d-n"),
          el("td", {}, patientLink(flag)),
          el("td", {}, referLine(flag.sign, flag.label),
            el("span", { class: "d-when" }, el("span", { text: "Flagged on" }), " ", raw("span", shortDate(flag.at)))),
          el("td", {}, quote(flag.quote)),
          el("td", { class: "d-col-step" }, track),
          el("td", { class: "d-col-act" }, button || el("span", { class: "d-tag", text: "Closed" })));
      })));
  }

  function drawHome() {
    if (!board) return;
    drawCrumbs(["Overview"]);
    view.replaceChildren(
      hero(),
      stats(),
      el("div", { class: "d-grid" }, mustReview(), visitsDue()),
      panel({ id: "flags", title: "Danger flags", iconName: "flag", count: board.flags.length, danger: true,
        help: "A flag stays open until the ANM closes it. A later “No” never clears it." },
        board.flags.length ? flagTable(board.flags) : empty("No open danger flags.")));
  }

  // ---------- results: tag, village or typed search ----------

  function resultTable(found) {
    return el("table", { class: "d-table" },
      el("thead", {}, el("tr", {},
        el("th", { class: "d-n" }, el("span", { class: "d-sr", text: "Number" })),
        el("th", { text: "Patient" }), el("th", { text: "ID" }), el("th", { text: "Village" }),
        el("th", { text: "Visit type" }), el("th", { text: "Next visit" }), el("th", { text: "Danger sign" }))),
      el("tbody", {}, found.map((p, i) => el("tr", { "data-href": "",
        onclick: event => { if (!event.target.closest("a")) openPatientPage(p.id); } },
        raw("td", String(i + 1).padStart(2, "0"), "d-n"),
        el("td", {}, el("a", { class: "d-who", href: `?patient=${encodeURIComponent(p.id)}`,
          onclick: event => { event.preventDefault(); openPatientPage(p.id); } }, raw("span", p.name, "d-who-name"))),
        raw("td", p.id, "d-nowrap"),
        raw("td", p.village),
        el("td", { text: TYPES[p.visit_type] || p.visit_type }),
        el("td", {}, dueBadge(p.due)),
        el("td", {}, p.open_flags ? el("span", { class: "d-tag is-danger", text: "Refer to PHC" }) : null)))));
  }

  function drawResults({ tag, village, query }) {
    if (!board) return;
    let found = board.patients;
    let heading;
    if (tag) {
      found = found.filter(p => p.tags.includes(tag));
      heading = el("h1", { text: tagLabel(tag) });
      drawCrumbs(["Filters"], [tagLabel(tag)]);
    }
    if (village) {
      found = found.filter(p => p.village === village);
      heading = raw("h1", village);
      drawCrumbs(["Villages"], [village, null, true]);
    }
    if (query) {
      found = matches(query).filter(m => m.kind === "patient").map(m => m.item);
      heading = el("h1", { text: `Results for “${query}”` });
      drawCrumbs(["Search"]);
    }
    found = [...found].sort(byDue);
    view.replaceChildren(
      el("div", { class: "d-page-head" }, heading, el("span", { class: "d-count", text: String(found.length) }),
        el("button", { type: "button", class: "d-link", onclick: () => { navAt = "overview"; go({}); }, text: "Clear filter" })),
      el("section", { class: "d-panel" },
        found.length ? resultTable(found) : empty("No patient found. Try a name, ID or village.")));
  }

  // ---------- one patient ----------

  function sparkline(series, field) {
    const values = series.points.map(p => (field === "bp" ? p.value : [p.value]));
    const flat = values.flat();
    const lo = Math.min(...flat), hi = Math.max(...flat);
    const W = 120, H = 36, pad = 4;
    const x = i => (values.length === 1 ? W / 2 : pad + (i * (W - 2 * pad)) / (values.length - 1));
    const y = v => (hi === lo ? H / 2 : H - pad - ((v - lo) * (H - 2 * pad)) / (hi - lo));
    const lines = (field === "bp" ? [0, 1] : [0]).map(k => {
      const pts = values.map((v, i) => `${x(i).toFixed(1)},${y(v[k]).toFixed(1)}`).join(" ");
      return `<polyline points="${pts}"/><circle cx="${x(values.length - 1)}" cy="${y(values.at(-1)[k])}" r="2.6"/>`;
    }).join("");
    const svg = el("span", { class: "d-spark", "aria-hidden": "true" });
    svg.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${lines}</svg>`;
    return svg;
  }

  function trends(timeline) {
    const fields = ["weight_kg", "hb", "bp"].filter(f => timeline[f]);
    if (!fields.length) return null;
    const dirs = { higher: "Higher", lower: "Lower", same: "Same" };
    return panel({ title: "Trends", iconName: "trend" },
      el("ul", { class: "d-trends" }, fields.map(field => {
        const series = timeline[field];
        const last = series.points.at(-1);
        const first = series.points[0];
        return el("li", { class: "d-trend" },
          el("span", { class: "d-trend-name", text: FIELDS[field] }),
          sparkline(series, field),
          el("span", { class: "d-trend-value" }, raw("span", format(field, last.value)),
            series.direction ? el("span", { class: "d-dir", text: dirs[series.direction] }) : null),
          el("span", { class: "d-trend-range" }, raw("span", `${shortDate(first.date)} → ${shortDate(last.date)}`)));
      })),
      el("p", { class: "d-help d-panel-foot", text: "Higher, Lower or Same compares the last two readings. It is not a judgement." }));
  }

  function visitCard(visit) {
    const record = Object.entries(visit.record || {}).filter(([k, v]) => v != null && FIELDS[k]);
    const present = (visit.receipt || []).filter(r => r.status === "present");
    return el("details", { class: "d-visit", id: `visit-${visit.id}` },
      el("summary", {},
        el("span", { class: "d-visit-date" }, raw("span", shortDate(visit.saved_at))),
        el("span", { class: "d-visit-type", text: TYPES[visit.visit_type] || visit.visit_type }),
        present.length ? el("span", { class: "d-tag is-danger", text: "Danger sign" }) : null),
      el("div", { class: "d-visit-body" },
        record.length ? el("dl", { class: "d-fields" }, record.map(([k, v]) =>
          el("div", {}, el("dt", { text: FIELDS[k] }), el("dd", {}, raw("span", format(k, v)))))) : null,
        present.map(r => referLine(r.sign, r.label)),
        el("button", { type: "button", class: "d-btn d-print-btn", onclick: () => printVisit(visit) },
          icon("print"), el("span", { text: "Print this visit" })),
        el("h4", { class: "d-h4", text: "Audit trail" }),
        el("ol", { class: "d-audit" }, (visit.audit || []).map(a => el("li", {},
          raw("time", new Date(a.at).toLocaleString(locale(), { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" })),
          el("span", { class: "d-audit-what" },
            el("strong", { text: AUDIT[a.kind] || a.kind }),
            a.sign && a.kind !== "visit_switch" ? [": ", raw("span", signName(a.sign))] : null,
            a.by ? el("span", { class: "d-audit-by" }, el("span", { text: BY[a.by] || a.by })) : null))))));
  }

  async function openPatient(id) {
    const token = ++loadToken;
    drawCrumbs(["Patient"]);
    view.replaceChildren(el("p", { class: "d-note", text: "Loading…" }));
    let data;
    try {
      const text = await fetchText(`/api/patients/${encodeURIComponent(id)}`);
      data = JSON.parse(text);
      lastPatient = text;
    } catch (error) {
      console.error(error);
      if (token === loadToken) view.replaceChildren(el("p", { class: "d-error", role: "alert", text: "Could not load this patient." }));
      return;
    }
    if (token !== loadToken) return;
    patient = data;
    drawPatient();
    document.getElementById(location.hash.slice(1))?.setAttribute("open", "");
  }

  function flagCard(flag) {
    const [track, button] = ladder(flag);
    return el("article", { class: "d-flagcard" },
      el("div", { class: "d-flag-what" }, referLine(flag.sign, flag.label), quote(flag.quote), when(flag.at)),
      el("div", { class: "d-flag-track" }, track, button));
  }

  function profile(p, due) {
    return el("section", { class: "d-profile" },
      raw("span", initials(p.name), "d-avatar"),
      el("div", {},
        raw("h1", p.name, "d-patient-name"),
        el("p", { class: "d-profile-meta" }, raw("span", `ID ${p.id}`), raw("span", p.village),
          el("span", { text: TYPES[p.visit_type] || p.visit_type }),
          p.relation_name ? el("span", {}, el("span", { text: relationLabel(p.relation) }), ": ", raw("span", p.relation_name)) : null)),
      el("div", { class: `d-duebox is-${due.state}` },
        el("span", { class: "d-due-label", text: "Next visit" }),
        el("strong", { text: dueText(due) }),
        due.date ? el("span", { class: "d-due-meta" }, raw("span", shortDate(due.date)), " · ",
          el("span", { text: due.basis === "dictated" ? "Date she gave" : "Usual gap for this visit type" })) : null));
  }

  function drawPatient() {
    if (!patient) return;
    const p = patient.patient;
    const review = patient.review.length + patient.checks.length;
    drawCrumbs([p.name, null, true]);
    const left = el("div", { class: "d-stack" },
      patient.open_flags.length
        ? panel({ title: "Danger flags", iconName: "flag", count: patient.open_flags.length, danger: true },
            patient.open_flags.map(flagCard))
        : null,
      review
        ? panel({ title: "Must review", iconName: "review", count: review, cls: "d-must has-items" },
            el("ol", { class: "d-rows" }, patient.review.map(i => reportRow(i, false)), patient.checks.map(i => checkRow(i, false))))
        : null,
      panel({ title: "Visits", iconName: "list", count: patient.visits.length },
        patient.visits.length ? el("div", {}, patient.visits.map(visitCard)) : empty("No visits saved yet.")));
    const right = el("div", { class: "d-stack" },
      panel({ title: "Ask at next visit", iconName: "ask", count: patient.not_asked.length },
        patient.not_asked.length
          ? [el("ul", { class: "d-ask" }, patient.not_asked.map(s => el("li", {}, raw("span", signName(s.sign, s.label))))),
             el("p", { class: "d-help d-panel-foot", text: "Not asked last time. Not asked is never a “No”." })]
          : empty("Every sign was asked last time.")),
      trends(patient.timeline));
    view.replaceChildren(
      el("div", { class: "d-page-actions" },
        el("button", { type: "button", class: "d-back", onclick: () => (history.length > 1 ? history.back() : go({})) },
          icon("back"), el("span", { text: "Back" })),
        patient.visits.length ? el("button", { type: "button", class: "d-btn d-btn-primary d-print-btn",
          onclick: () => printVisit(patient.visits[0]) }, icon("print"), el("span", { text: "Print report" })) : null),
      profile(p, patient.due),
      el("div", { class: "d-cols" }, left, right));
  }

  // ---------- printed visit form (laid out like the paper HBNC / MCP home-visit form) ----------

  const MARKS = [["present", "Yes"], ["ruled_out", "No"], ["not_checked", "Not checked"]];
  const box = on => raw("span", on ? "☑" : "☐", "p-box");

  function printVisit(visit) {
    const p = patient.patient;
    const number = patient.visits.length - patient.visits.indexOf(visit);
    const receipt = visit.receipt || [];
    const present = receipt.filter(r => r.status === "present");
    const record = Object.entries(visit.record || {}).filter(([k, v]) => v != null && FIELDS[k]);
    const cell = (label, value, isRaw = true) => el("div", { class: "p-cell" },
      el("span", { class: "p-label", text: label }), isRaw ? raw("span", value ?? "", "p-value") : el("span", { class: "p-value", text: value }));
    const sheet = el("article", { class: "p-sheet", id: "print-sheet" },
      el("header", { class: "p-head" },
        el("div", {}, el("p", { class: "p-kicker", text: "Visit Relay" }),
          el("h1", {}, el("span", { text: TYPES[visit.visit_type] || visit.visit_type }), " ", el("span", { text: "home-visit record" }))),
        el("div", { class: "p-head-no" }, el("span", { text: "Visit no." }), raw("strong", String(number)))),
      el("section", {}, el("h2", { text: "1. Beneficiary details" }),
        el("div", { class: "p-grid" },
          cell("Name", p.name), cell("ID", p.id), cell("Village", p.village),
          cell(relationLabel(p.relation) || "Husband", p.relation_name || "—"),
          cell("Visit date", new Date(visit.saved_at).toLocaleDateString(locale(), { day: "numeric", month: "short", year: "numeric" })),
          cell("Visit type", TYPES[visit.visit_type] || visit.visit_type, false))),
      el("section", {}, el("h2", { text: "2. Measurements" }),
        record.length
          ? el("table", { class: "p-table" }, el("tbody", {}, record.map(([k, v]) =>
              el("tr", {}, el("th", { text: FIELDS[k] }), el("td", {}, raw("span", format(k, v)))))))
          : el("p", { text: "Nothing measured at this visit." })),
      el("section", {}, el("h2", { text: "3. Danger signs" }),
        el("table", { class: "p-table p-signs" },
          el("thead", {}, el("tr", {}, el("th", { text: "#" }), el("th", { text: "Danger sign" }),
            MARKS.map(([, label]) => el("th", { class: "p-mark", text: label })), el("th", { text: "What was said" }))),
          el("tbody", {}, receipt.map((r, i) => el("tr", { class: r.status === "present" ? "is-yes" : null },
            raw("td", String(i + 1)), el("td", {}, raw("span", signName(r.sign, r.label))),
            MARKS.map(([status]) => el("td", { class: "p-mark" }, box(r.status === status))),
            el("td", {}, raw("span", r.quote ? `“${r.quote}”` : "")))))),
        el("p", { class: "p-note", text: "Not checked is never a “No”. Ask these at the next visit." })),
      el("section", {}, el("h2", { text: "4. Action" }),
        el("p", { class: "p-action" }, box(present.length > 0), " ", el("strong", { text: "Refer to PHC" }),
          present.length ? [" — ", raw("span", present.map(r => signName(r.sign, r.label)).join(", "))] : null),
        el("p", { class: "p-action" }, box(present.length === 0), " ", el("span", { text: "No danger sign recorded" })),
        visit.record?.next_visit_date ? el("p", {}, el("strong", { text: "Next visit" }), ": ", raw("span", format("next_visit_date", visit.record.next_visit_date))) : null),
      el("footer", { class: "p-sign" },
        el("div", {}, el("span", { class: "p-line" }), el("span", { text: "ASHA name and signature" })),
        el("div", {}, el("span", { class: "p-line" }), el("span", { text: "ANM signature and date" }))),
      el("p", { class: "p-foot", text: "Recorded by voice in Visit Relay. It does not diagnose. All patients are made up." }));
    document.getElementById("print-sheet")?.remove();
    document.body.append(sheet);
    // let i18n translate the new text first
    requestAnimationFrame(() => requestAnimationFrame(() => window.print()));
  }
  window.addEventListener("afterprint", () => document.getElementById("print-sheet")?.remove());

  // ---------- language ----------

  const savedLang = store.get(LANG_KEY, null);
  if (savedLang && [...langSelect.options].some(o => o.value === savedLang)) langSelect.value = savedLang;
  else langSelect.value = "en";
  langSelect.addEventListener("change", () => store.set(LANG_KEY, langSelect.value));
  window.addEventListener("i18n:change", () => {
    if (!board) return;
    if (params().get("patient") && patient) { drawNav(); drawPatient(); } else route();
  });

  // ---------- auto-refresh: visits saved on the phone show up without a reload ----------

  const REFRESH_MS = 30000;
  let refreshing = false;

  // Never redraw under someone typing, picking from search or waiting on a save.
  const interacting = () => document.hidden || !list.hidden
    || document.activeElement?.matches("input, select, textarea") || Boolean(document.querySelector("[aria-busy]"));

  async function refresh() {
    if (refreshing || !board || interacting()) return;
    refreshing = true;
    try {
      const id = params().get("patient");
      const boardText = await fetchText("/api/dashboard");
      const patientText = id ? await fetchText(`/api/patients/${encodeURIComponent(id)}`) : lastPatient;
      if ((boardText === lastBoard && patientText === lastPatient) || interacting() || params().get("patient") !== id) return;
      board = JSON.parse(boardText);
      lastBoard = boardText;
      if (id) { patient = JSON.parse(patientText); lastPatient = patientText; }
      redraw();
    } catch (error) {
      console.error("Dashboard refresh failed; will try again.", error);
    } finally {
      refreshing = false;
    }
  }

  // Redraw in place: keep the scroll position and any visit the reader had opened.
  function redraw() {
    const y = window.scrollY;
    const open = [...view.querySelectorAll("details[open]")].map(d => d.id);
    if (params().get("patient")) { drawNav(); drawPatient(); } else route();
    open.forEach(id => document.getElementById(id)?.setAttribute("open", ""));
    window.scrollTo(0, y);
  }

  setInterval(refresh, REFRESH_MS);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
  window.addEventListener("focus", refresh);

  // ---------- close suggestions on outside click; start ----------

  document.addEventListener("pointerdown", event => {
    if (!event.target.closest(".d-search")) closeSuggest();
  });
  window.addEventListener("popstate", route);

  loadBoard().then(route, error => {
    console.error(error);
    view.replaceChildren(el("p", { class: "d-error", role: "alert", text: "Could not load the dashboard." }));
  });
})();
