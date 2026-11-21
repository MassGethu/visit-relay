// Screen cards for the phone page. app.js calls window.Cards.handle(event) for every backend event;
// everything here is drawn inside <main id="cards">. Text always goes in via textContent (never HTML).
(() => {
  "use strict";

  const VISIT_TYPES = { anc: "ANC", pnc: "PNC", hbnc: "HBNC", hbyc: "HBYC" };
  const VISIT_NAMES = { anc: "ANC · pregnancy", pnc: "PNC · mother after delivery",
    hbnc: "HBNC · newborn", hbyc: "HBYC · young child" };
  const SWITCH_WAIT_MS = 4000;           // no reply from the backend: put the dropdown back
  const STATUS_TEXT = { present: "Present", ruled_out: "Ruled out", not_checked: "Not checked" };
  const VITALS = ["gestational_month", "weight_kg", "bp", "hb", "temperature", "breaths_per_min"];
  const FIELDS = {
    gestational_month: ["Pregnancy month", v => String(v)],
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
    context: null,                       // {current, suggested}: the backend asks "which visit is this?"
    switching: "", switchNote: "", switchTimer: null, checklist: [], sessionId: null,
    report: null, reportMessage: "", filing: false, filed: null,
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
    const personPicker = state.started || !state.people.length ? [] : [
      el("label", { for: "c-person", text: "Visit for" }),
      el("select", { id: "c-person", onchange: e => choose(e.target.value) },
        state.people.map(p => el("option", { value: p.id, selected: p === person,
          text: `${p.name} · ID ${p.id}` }))),
    ];
    // The visit type stays changeable during the visit: the fallback when she or the app got it wrong.
    const typePicker = state.saved ? [] : [
      el("label", { for: "c-type", text: state.started ? "Visit type (change if wrong)" : "Visit type" }),
      el("select", { id: "c-type", disabled: Boolean(state.switching),
        onchange: e => (state.started ? requestSwitch(e.target.value) : pickType(e.target.value)) },
        Object.entries(VISIT_NAMES).map(([value, text]) =>
          el("option", { value, text, selected: value === (state.switching || state.visitType) }))),
      state.switching && el("p", { class: "c-pending", text: `Switching to ${VISIT_TYPES[state.switching]}…` }),
      state.switchNote && el("p", { class: "c-pending", text: state.switchNote }),
    ];
    visitCard.replaceChildren(who, ...personPicker, ...typePicker);
  }

  function pickType(visitType) {
    state.visitType = visitType;
    drawVisit();
    loadChecklist();
  }

  // app.js listens for "cards:send" and forwards the detail to the backend WebSocket.
  function send(message) {
    window.dispatchEvent(new CustomEvent("cards:send", { detail: message }));
  }

  function requestSwitch(visitType) {
    state.context = null;
    state.switchNote = "";
    if (!(visitType in VISIT_TYPES) || visitType === state.visitType) {
      state.switching = "";
      if (visitType === state.visitType) send({ type: "set_visit_type", visit_type: visitType });
      drawVisit();
      drawLive();
      return;
    }
    state.switching = visitType;
    clearTimeout(state.switchTimer);
    state.switchTimer = setTimeout(() => {
      state.switching = "";
      state.switchNote = "Could not change the visit type. Try again.";
      drawVisit();
    }, SWITCH_WAIT_MS);
    send({ type: "set_visit_type", visit_type: visitType });
    drawVisit();
    drawLive();
  }

  function switched(event) {
    clearTimeout(state.switchTimer);
    const from = state.visitType;
    state.switching = "";
    state.context = null;
    if (event.visit_type in VISIT_TYPES) state.visitType = event.visit_type;
    state.switchNote = from !== state.visitType
      ? `Changed from ${VISIT_TYPES[from]}. Everything said so far was checked again.` : "";
    drawVisit();
    loadChecklist();
  }

  function drawContext() {
    const ctx = state.context;
    if (!ctx) return null;
    const choices = [ctx.current, ...ctx.suggested].filter(v => v in VISIT_TYPES);
    return el("section", { class: "c-card c-context", "aria-label": "Which visit is this?" },
      el("div", { class: "c-kicker", text: "Which visit is this?" }),
      el("p", { text: "Answer by voice, or tap:" }),
      el("div", { class: "c-choices" }, choices.map(v => el("button", {
        class: `c-button${v === ctx.current ? "" : " c-switch"}`, type: "button",
        text: v === ctx.current ? `Keep ${VISIT_NAMES[v]}` : `Switch to ${VISIT_NAMES[v]}`,
        onclick: () => requestSwitch(v) }))));
  }

  function choose(id) {
    state.person = state.people.find(p => String(p.id) === String(id)) || null;
    if (state.person?.visit_type in VISIT_TYPES) state.visitType = state.person.visit_type;
    drawVisit();
    loadChecklist();
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

  // Her concerns outside the checklist, verbatim. They never change a checklist state.
  const concernsOf = record => (Array.isArray(record.worker_concerns) ? record.worker_concerns : []);
  // Signs flagged on the earlier visit type's checklist: they stay flagged after a switch.
  const flagsBeforeSwitch = record => (Array.isArray(record.flags_before_switch) ? record.flags_before_switch : []);
  const NOT_FIELDS = new Set(["worker_concerns", "flags_before_switch"]);

  function concernItem(concern) {
    return el("li", { class: "c-concern" },
      el("span", { class: "c-quote", text: `“${concern.quote}”` }),
      el("span", { class: `c-flag${concern.flagged ? " on" : ""}`,
        text: concern.flagged ? "Flagged for ANM" : "Noted — say “ANM ko batao” to flag" }));
  }

  let checklistRequest = 0;

  async function loadChecklist() {
    const request = ++checklistRequest;
    const lang = document.querySelector("#speech-language").value;
    state.checklist = [];
    drawLive();
    try {
      const response = await fetch(`/api/checklist/${state.visitType}?lang=${lang}`);
      if (!response.ok) throw new Error("Checklist unavailable");
      const questions = await response.json();
      if (request === checklistRequest) {
        state.checklist = questions;
        drawLive();
      }
    } catch {
      if (request === checklistRequest) {
        state.checklist = null;
        drawLive();
      }
    }
  }

  function currentQuestion() {
    return state.checklist?.find(item => state.question === speechText(item.question));
  }

  function assistantTranscriptText(text) {
    const spoken = speechText(text);
    const question = currentQuestion();
    if (!question) return text;
    const full = speechText(question.question);
    const [first, ...instructions] = full.split(/(?<=[.!?।])\s+/u);
    if (spoken === full || spoken === first) return `Question ${question.number} · Unanswered`;
    if (instructions.includes(spoken)) return "";
    return text;
  }

  function drawChecklist() {
    const receipt = new Map((state.receipt || []).map(row => [row.sign, row]));
    const fields = ["gestational_month", ...VITALS.filter(field => field !== "gestational_month"), "next_visit_date"]
      .filter(field => field !== "gestational_month" || state.visitType === "anc");
    const checklist = state.checklist;
    return el("section", { class: "c-card c-template", "aria-label": "Visit questions" },
      el("h2", { text: "Visit questions" }),
      el("p", { class: "c-empty", text: "Review these questions, then dictate what you know. Say “not sure” for a question you cannot answer." }),
      el("dl", { class: "c-fields" }, fields.map(field => {
        const [label, value] = fieldText(field, state.record[field]);
        const missing = state.record[field] == null;
        return el("div", { class: "c-field" }, el("dt", { text: label }),
          el("dd", { class: missing ? "c-missing" : "", text: missing ? "Not recorded" : value }));
      })),
      checklist?.length ? el("ol", { class: "c-checklist" }, checklist.map(item => {
        const row = receipt.get(item.sign);
        const status = row?.status || "not_checked";
        const current = state.question === speechText(item.question);
        return el("li", { class: `is-${status}${current ? " c-current-question" : ""}`,
          "aria-current": current ? "true" : null },
          el("span", { class: "c-q", text: speechText(item.display_question ?? item.question) }),
          el("div", { class: "c-meta" },
            el("span", { class: `c-status ${status}`, text: STATUS_TEXT[status] || "Not checked" }),
            row?.quote && el("small", { class: "c-said", text: `“${row.quote}”` })));
      })) : el("p", { class: "c-empty", text: checklist ? "Loading safety questions…" : "Could not load safety questions." }));
  }

  function dangerPreview() {
    if (!state.receipt || state.saved) return null;
    const flagged = state.receipt.filter(row => row.status === "present");
    const present = flagged.length;
    const checked = state.receipt.filter(row => row.status === "ruled_out").length;
    return el("section", { class: "c-card", "aria-label": "Danger report preview" },
      el("h2", { text: "Danger report" }),
      el("ul", { class: "c-counts", "aria-label": "Sign counts" }, [
        ["present", present, "present"],
        ["ruled_out", checked, "ruled out"],
        ["not_checked", state.receipt.length - present - checked, "not checked"],
      ].map(([status, count, label]) => el("li", { class: `c-count ${status}${count ? "" : " zero"}` },
        el("strong", { text: String(count) }), el("span", { text: label })))),
      el("p", { class: "c-empty", text: present
        ? "Review the cited flags and the PHC referral shown above."
        : "No checklist signs flagged. Review anything still unchecked." }),
      el("details", {}, el("summary", { text: "Review all signs" }),
        el("ul", {}, state.receipt.map(receiptRow))));
  }

  function drawLive() {
    const names = Object.keys(state.record).filter(name => !NOT_FIELDS.has(name));
    const before = flagsBeforeSwitch(state.record);
    const concerns = concernsOf(state.record);
    const rows = names.map(name => {
      const [label, value] = fieldText(name, state.record[name]);
      const said = state.evidence[name];
      return el("div", { class: `c-field${state.changed.has(name) ? " c-new" : ""}` },
        el("dt", { text: label }), el("dd", { text: value }),
        said && el("dd", { class: "c-said", text: `“${said}”` }));
    });
    const activeQuestion = currentQuestion();
    const question = state.question && el("section", {
      class: `c-card c-question${state.speaking ? " c-speaking" : ""}`, "aria-live": "polite" },
      el("p", { text: activeQuestion ? `Question ${activeQuestion.number} · Unanswered` : state.question }));
    const record = el("section", { class: "c-card", "aria-label": "Visit record" },
      el("h2", { text: "Visit record" }),
      rows.length ? el("dl", { class: "c-fields" }, rows)
        : el("p", { class: "c-empty", text: "Fields fill in as she speaks." }),
      concerns.length && el("div", { class: "c-concerns" },
        el("h3", { text: "Worker concerns (her words)" }),
        el("ul", {}, concerns.map(concernItem))),
      before.length && el("div", { class: "c-concerns" },
        el("h3", { text: "Flagged before the visit type changed" }),
        el("ul", {}, before.map(f => el("li", { class: "c-concern" },
          el("span", { text: `${f.label} (${VISIT_TYPES[f.visit_type] || f.visit_type}) — refer to PHC` }),
          f.quote && el("span", { class: "c-quote", text: `“${f.quote}”` }))))));
    const preview = dangerPreview();
    if (preview && liveBox.querySelector("[aria-label='Danger report preview'] details")?.open) {
      preview.querySelector("details").open = true;
    }
    liveBox.replaceChildren(...[drawContext(), drawChecklist(), question, record, preview].filter(Boolean));
    state.changed.clear();
  }

  function receiptRow(row) {
    const local = row.local && row.local !== row.label ? row.local : "";
    return el("li", { class: "c-row" },
      el("div", { class: "c-name" },
        el("span", { text: local || row.label }),
        local && el("small", { text: row.label }),
        row.quote && el("span", { class: "c-quote", text: `“${row.quote}”` }),
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
    const present = [...(state.receipt || []).filter(r => r.status === "present"),
      ...flagsBeforeSwitch(state.record)];
    const flagged = concernsOf(state.record).filter(c => c.flagged);
    const vitals = VITALS.filter(f => f in state.record).map(f => fieldText(f, state.record[f]).join(": "));
    return el("section", { class: "c-card c-anm", "aria-label": "ANM referral card" },
      el("h2", { text: "ANM / PHC card" }),
      el("p", { text: `${person ? `${person.name} · ID ${person.id}` : "Synthetic beneficiary"} · `
        + `${VISIT_TYPES[state.visitType] || state.visitType} · ${timeText(state.savedAt)}` }),
      present.length ? present.map(r => [
        el("p", { class: "c-sign", text: `${r.label} — refer to PHC` }),
        r.quote && el("p", { class: "c-quote", text: `ASHA said: “${r.quote}”` }),
      ]) : el("p", { class: "c-empty", text: "No checklist signs flagged." }),
      flagged.length && el("div", { class: "c-concerns" },
        el("h3", { text: "Worker concern — ASHA asked ANM to review" }),
        flagged.map(c => el("p", { class: "c-quote", text: `ASHA said: “${c.quote}”` }))),
      vitals.length && el("p", { text: `Recorded: ${vitals.join(" · ")}` }),
      el("p", { class: "c-note", text: "No diagnosis made by AI. Synthetic data." }));
  }

  async function loadReport() {
    const id = state.sessionId;
    if (!id) return;
    try {
      const response = await fetch(`/api/visit-report/${id}`);
      if (!response.ok) throw new Error();
      const report = await response.json();
      if (id === state.sessionId && state.saved) state.report = report;
    } catch {
      if (id === state.sessionId) state.reportMessage = "Could not load the confirmed report.";
    }
    if (id === state.sessionId) drawEnd();
  }

  async function fileReport() {
    const id = state.sessionId;
    state.filing = true;
    state.reportMessage = "";
    drawEnd();
    try {
      const response = await fetch(`/api/visit-report/${id}/file`, { method: "POST" });
      if (!response.ok) throw new Error();
      const filed = await response.json();
      if (id === state.sessionId && state.saved) state.filed = filed;
    } catch {
      if (id === state.sessionId) state.reportMessage = "Dashboard filing failed. Try again.";
    } finally {
      if (id === state.sessionId) {
        state.filing = false;
        drawEnd();
      }
    }
  }

  function drawReport() {
    const report = state.report;
    const previous = report?.previous_date;
    return el("section", { class: "c-card", "aria-label": "Confirmed visit report" },
      el("h2", { text: "Confirmed visit report" }),
      report && el("p", { class: "c-empty", text: previous
        ? `Compared with ${report.seeded_baseline ? "the synthetic baseline" : "the previous visit"} on ${previous.slice(0, 10)}.`
        : "No earlier visit of this type is available." }),
      previous && report.changes.length > 0 && el("ul", {}, report.changes.map(change => {
        const [label, before] = fieldText(change.field, change.before);
        const [, after] = fieldText(change.field, change.after);
        return el("li", { text: `${label}: ${before} → ${after}` });
      })),
      report && previous && report.changes.length === 0 &&
        el("p", { class: "c-empty", text: "No matching measurements to compare." }),
      report && report.new_flags.length > 0 && el("p", { text: `New flags: ${report.new_flags.map(sign => report.receipt.find(row => row.sign === sign)?.label || sign).join(", ")}` }),
      report && report.recurring_flags.length > 0 && el("p", { text: `Recurring flags: ${report.recurring_flags.map(sign => report.receipt.find(row => row.sign === sign)?.label || sign).join(", ")}` }),
      state.reportMessage && el("p", { role: "status", text: state.reportMessage }),
      !report && !state.reportMessage && el("p", { role: "status", text: "Preparing report…" }),
      !report && state.reportMessage && el("button", { class: "c-button", type: "button",
        text: "Reload report", onclick: loadReport }),
      report && !state.filed && el("button", { class: "c-button", type: "button",
        text: state.filing ? "Filing report…" : "Push to dashboard", disabled: state.filing, onclick: fileReport }),
      state.filed && el("a", { class: "c-button",
        href: `/dashboard.html?patient=${encodeURIComponent(state.filed.beneficiary_id)}#visit-${state.filed.visit_id}`,
        text: "Open patient history" }));
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
      drawReport(),
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
        drawLive();
        break;
      case "saved":
        state.saved = true;
        state.undone = false;
        state.savedAt = new Date();
        state.question = "";
        state.context = null;
        drawVisit();
        drawLive();
        drawEnd();
        loadReport();
        break;
      case "visit_context":
        state.context = { current: event.current || state.visitType,
          suggested: Array.isArray(event.suggested) ? event.suggested : [] };
        drawLive();
        break;
      case "visit_type":
        switched(event);
        break;
      case "transcript":                 // she spoke again: the "which visit?" question is answered or lapsed
        if (state.context) {
          state.context = null;
          drawLive();
        }
        break;
      case "undo":
        state.saved = false;
        state.undone = true;
        state.showAnm = false;
        state.report = null;
        state.filed = null;
        drawVisit();
        drawEnd();
        break;
      default:
        break;                           // latency: shown by app.js
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
      if (!state.started && !state.sessionId) choose(state.people[0]?.id);
    } catch (error) {
      console.warn("cards: could not load beneficiaries:", error);
      drawVisit();
    }
  }

  function endSession() {
    clearTimeout(state.switchTimer);
    Object.assign(state, {
      started: false, record: {}, evidence: {}, changed: new Set(), alerts: new Set(),
      question: "", speaking: false, discreet: false, receipt: null, saved: false,
      savedAt: null, showAnm: false, undone: false, context: null, switching: "", switchNote: "",
      sessionId: null, report: null, reportMessage: "", filing: false, filed: null,
    });
    alertBox.replaceChildren();
    drawVisit();
    drawLive();
    drawEnd();
    loadChecklist();
  }

  document.querySelector("#speech-language").addEventListener("change", loadChecklist);
  window.Cards = {
    handle, endSession, assistantTranscriptText,
    startSession: (id, person) => {
      state.sessionId = id;
      if (person) {
        state.person = person;
        state.visitType = person.visit_type;
        state.started = true;
        drawVisit();
      }
    },
    // The chosen beneficiary and visit type, for app.js's start_visit message.
    beneficiary: () => (state.person ? { ...state.person, visit_type: state.visitType } : null),
  };
  drawVisit();
  drawLive();
  loadPeople();
})();
