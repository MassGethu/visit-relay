// Screen cards for the phone page. app.js calls window.Cards.handle(event) for every backend event;
// everything here is drawn inside <main id="cards">. Text always goes in via textContent (never HTML).
(() => {
  "use strict";

  const VISIT_TYPES = { anc: "ANC", pnc: "PNC", hbnc: "HBNC", hbyc: "HBYC" };
  const STATUS_TEXT = { present: "Present", ruled_out: "Ruled out", not_checked: "Not checked" };
  const VITALS = ["weight_kg", "bp", "hb", "temperature", "breaths_per_min"];
  const FIELDS = {
    weight_kg: ["Weight", v => `${v} kg`],
    bp: ["BP", v => `${v[0]}/${v[1]}`],
    hb: ["Hb", v => `${v} g/dL`],
    temperature: ["Temperature", v => `${v[0]} °${v[1]}`],
    breaths_per_min: ["Breathing", v => `${v} / min`],
    next_visit_date: ["Next visit", v => formatDate(v)],
    next_visit_text: ["Next visit (said)", v => v],
    ifa_taking: ["IFA tablets", v => (v ? "Taking" : "Not taking")],
    vaccinations_given: ["Vaccines given", v => v.join(", ")],
    vaccinations_due: ["Vaccines due", v => v.join(", ")],
  };

  const state = {
    people: [], person: null, visitType: "anc", started: false,
    record: {}, evidence: {}, changed: new Set(), alerts: new Set(),
    question: "", speaking: false, discreet: false,
    receipt: null, saved: false, savedAt: null, showAnm: false, undone: false,
  };

  // ---------- small DOM helpers ----------

  function el(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else if (value !== false && value != null) node.setAttribute(key, value === true ? "" : value);
    }
    for (const child of children.flat(Infinity)) if (child) node.append(child);
    return node;
  }

  const speechText = text => String(text || "").replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim();
  const timeText = date => date.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });

  function formatDate(iso) {
    const date = new Date(`${iso}T00:00:00`);
    return Number.isNaN(date.getTime()) ? String(iso)
      : date.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
  }

  function fieldText(name, value) {
    const [label, format] = FIELDS[name] || [name.replace(/_/g, " "), v => String(v)];
    try { return [label, format(value)]; } catch { return [label, String(value)]; }
  }

  // ---------- layout: persistent parts + parts redrawn on each event ----------

  const root = document.getElementById("cards");
  if (!root) return;
  const visitCard = el("section", { class: "c-card c-visit", "aria-label": "Visit" });
  const alertBox = el("div", { class: "c-alerts", "aria-live": "assertive" });
  const liveBox = el("div", { class: "c-live" });
  const endBox = el("div", { class: "c-end" });
  root.append(visitCard, alertBox, liveBox, endBox);

  function drawVisit() {
    const person = state.person;
    const who = el("div", { class: "c-who" },
      el("span", { class: "c-big", text: person ? person.name : "Synthetic beneficiary" }),
      person && el("span", { class: "c-chip", text: `ID ${person.id}` }),
      el("span", { class: "c-chip", text: VISIT_TYPES[state.visitType] || state.visitType }),
      state.discreet && el("span", { class: "c-chip c-discreet", text: "Discreet mode" }));
    const pickers = state.started || !state.people.length ? [] : [
      el("label", { for: "c-person", text: "Visit for" }),
      el("select", { id: "c-person", onchange: e => choose(e.target.value) },
        state.people.map(p => el("option", { value: p.id, selected: p === person,
          text: `${p.name} · ID ${p.id}` }))),
      el("label", { for: "c-type", text: "Visit type" }),
      el("select", { id: "c-type", onchange: e => { state.visitType = e.target.value; drawVisit(); } },
        Object.entries(VISIT_TYPES).map(([value, text]) =>
          el("option", { value, text, selected: value === state.visitType }))),
    ];
    visitCard.replaceChildren(who, ...pickers);
  }

  function choose(id) {
    state.person = state.people.find(p => String(p.id) === String(id)) || null;
    if (state.person?.visit_type in VISIT_TYPES) state.visitType = state.person.visit_type;
    drawVisit();
  }

  function addAlert(event) {
    if (state.alerts.has(event.sign)) return;
    state.alerts.add(event.sign);
    const local = event.local && event.local !== event.label ? event.local : "";
    alertBox.prepend(el("section", { class: "c-alert", role: "alert" },
      el("div", { class: "c-kicker", text: "⚠ Danger sign" }),
      el("div", { class: "c-big", text: local || event.label }),
      local && el("div", { class: "c-en", text: event.label }),
      event.quote && el("p", { class: "c-quote", text: `“${event.quote}”` }),
      el("span", { class: "c-refer", text: "Refer to PHC" }),
      el("div", { class: "c-source", text: `Source: ${event.source || "—"}${event.page ? `, ${event.page}` : ""}` })));
  }

  function drawLive() {
    const names = Object.keys(state.record);
    const rows = names.map(name => {
      const [label, value] = fieldText(name, state.record[name]);
      const said = state.evidence[name];
      return el("div", { class: `c-field${state.changed.has(name) ? " c-new" : ""}` },
        el("dt", { text: label }), el("dd", { text: value }),
        said && el("dd", { class: "c-said", text: `“${said}”` }));
    });
    const question = state.question && el("section", {
      class: `c-card c-question${state.speaking ? " c-speaking" : ""}`, "aria-live": "polite" },
      el("p", { text: state.question }));
    const record = el("section", { class: "c-card", "aria-label": "Visit record" },
      el("h2", { text: "Visit record" }),
      rows.length ? el("dl", { class: "c-fields" }, rows)
        : el("p", { class: "c-empty", text: "Fields fill in as she speaks." }));
    liveBox.replaceChildren(...[question, record].filter(Boolean));
    state.changed.clear();
  }

  function receiptRow(row) {
    const local = row.local && row.local !== row.label ? row.local : "";
    return el("li", { class: "c-row" },
      el("div", { class: "c-name" },
        el("span", { text: local || row.label }),
        local && el("small", { text: row.label }),
        row.status !== "not_checked" && row.quote && el("span", { class: "c-quote", text: `“${row.quote}”` }),
        row.disputed && el("span", { class: "c-tag", text: "Disputed — ANM to check" }),
        row.history && row.status === "present" && el("span", { class: "c-tag", text: "Happened earlier" })),
      el("span", { class: `c-status ${row.status}`, text: STATUS_TEXT[row.status] || row.status }));
  }

  function drawReceipt() {
    const rows = state.receipt || [];
    const order = { present: 0, ruled_out: 1 };
    const checked = rows.filter(r => r.status !== "not_checked").sort((a, b) => order[a.status] - order[b.status]);
    const unchecked = rows.filter(r => r.status === "not_checked");
    return el("section", { class: "c-card c-receipt", "aria-label": "Danger-sign receipt" },
      el("h2", { text: "Danger-sign receipt" }),
      checked.length ? el("ul", {}, checked.map(receiptRow))
        : el("p", { class: "c-empty", text: "No danger sign was discussed." }),
      unchecked.length && el("details", {},
        el("summary", { text: `${unchecked.length} signs not checked (not asked — never a “No”)` }),
        el("ul", {}, unchecked.map(receiptRow))),
      el("div", { class: "c-foot" },
        el("span", { text: "Spoken by: ASHA" }),
        el("span", { text: `Time: ${timeText(state.savedAt)}` })));
  }

  function drawAnm() {
    const person = state.person;
    const present = (state.receipt || []).filter(r => r.status === "present");
    const vitals = VITALS.filter(f => f in state.record).map(f => fieldText(f, state.record[f]).join(": "));
    return el("section", { class: "c-card c-anm", "aria-label": "ANM referral card" },
      el("h2", { text: "ANM / PHC card" }),
      el("p", { text: `${person ? `${person.name} · ID ${person.id}` : "Synthetic beneficiary"} · `
        + `${VISIT_TYPES[state.visitType] || state.visitType} · ${timeText(state.savedAt)}` }),
      present.length ? present.map(r => [
        el("p", { class: "c-sign", text: `${r.label} — refer to PHC` }),
        r.quote && el("p", { class: "c-quote", text: `ASHA said: “${r.quote}”` }),
      ]) : el("p", { class: "c-empty", text: "No danger sign present." }),
      vitals.length && el("p", { text: `Recorded: ${vitals.join(" · ")}` }),
      el("p", { class: "c-note", text: "No diagnosis made by AI. Synthetic data." }));
  }

  function drawEnd() {
    if (!state.saved) {
      endBox.replaceChildren(...(state.undone
        ? [el("section", { class: "c-card", text: "Save undone. Tell me what to change." })] : []));
      return;
    }
    endBox.replaceChildren(
      el("section", { class: "c-card c-saved", role: "status" }, el("span", { text: "✓ Record saved" })),
      state.receipt && drawReceipt(),
      el("button", { class: "c-button", type: "button", "aria-expanded": String(state.showAnm),
        text: state.showAnm ? "Hide ANM card" : "Show ANM card",
        onclick: () => { state.showAnm = !state.showAnm; drawEnd(); } }),
      state.showAnm && drawAnm());
  }

  // ---------- events from the backend ----------

  function handle(event) {
    if (!event || typeof event.type !== "string") return;
    if (!state.started && event.type !== "latency") {
      state.started = true;              // the visit is running: lock the picker
      drawVisit();
    }
    switch (event.type) {
      case "record":
        for (const [name, value] of Object.entries(event.fields || {})) {
          if (JSON.stringify(state.record[name]) !== JSON.stringify(value)) state.changed.add(name);
        }
        state.record = { ...(event.fields || {}) };
        state.evidence = { ...(event.evidence || {}) };
        drawLive();
        break;
      case "alert":
        addAlert(event);
        break;
      case "question":
        state.question = speechText(event.text);
        drawLive();
        break;
      case "speaking":
        state.speaking = Boolean(event.on);
        drawLive();
        break;
      case "discreet":
        state.discreet = Boolean(event.on);
        drawVisit();
        break;
      case "receipt":
        state.receipt = Array.isArray(event.rows) ? event.rows : [];
        break;
      case "saved":
        state.saved = true;
        state.undone = false;
        state.savedAt = new Date();
        state.question = "";
        drawLive();
        drawEnd();
        break;
      case "undo":
        state.saved = false;
        state.undone = true;
        state.showAnm = false;
        drawEnd();
        break;
      default:
        break;                           // transcript, latency: shown by app.js
    }
  }

  async function loadPeople() {
    try {
      const response = await fetch("/api/beneficiaries");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const list = Array.isArray(data) ? data : data.beneficiaries || [];
      state.people = list.map(p => ({ ...p, id: String(p.id ?? p.beneficiary_id) }))
        .filter(p => p.id && p.id !== "undefined");
      choose(state.people[0]?.id);
    } catch (error) {
      console.warn("cards: could not load beneficiaries:", error);
      drawVisit();
    }
  }

  window.Cards = {
    handle,
    // The chosen beneficiary and visit type, for app.js's start_visit message.
    beneficiary: () => (state.person ? { ...state.person, visit_type: state.visitType } : null),
  };
  drawVisit();
  drawLive();
  loadPeople();
})();
