"use strict";

const patients = document.querySelector("#patient");
const status = document.querySelector("#history-status");
const historyList = document.querySelector("#history");
const requested = new URLSearchParams(location.search).get("patient");
let request = 0;

const types = { anc: "Antenatal", pnc: "Postnatal", hbnc: "Newborn", hbyc: "Young child" };
const labels = {
  gestational_month: "Pregnancy month", weight_kg: "Weight", hb: "Hb", bp: "BP",
  temperature: "Temperature", breaths_per_min: "Breathing", next_visit_date: "Next visit",
};
const states = { present: "Present", ruled_out: "Ruled out", not_checked: "Not checked" };

function node(tag, text) {
  const item = document.createElement(tag);
  if (text !== undefined) item.textContent = text;
  return item;
}

function format(field, value) {
  if (field === "weight_kg") return `${value} kg`;
  if (field === "hb") return `${value} g/dL`;
  if (field === "breaths_per_min") return `${value} / min`;
  if (field === "bp") return value.join("/");
  if (field === "temperature") return `${value[0]} °${value[1]}`;
  return Array.isArray(value) ? value.join(", ") : String(value);
}

function visitCard(visit) {
  const card = node("article");
  card.className = "c-card";
  card.id = `visit-${visit.id}`;
  card.append(node("h3", types[visit.visit_type] || visit.visit_type), node("p", visit.saved_at.slice(0, 10)));
  const fields = node("dl");
  fields.className = "c-fields";
  for (const [field, value] of Object.entries(visit.record)) {
    if (value == null || field === "worker_concerns" || field === "flags_before_switch") continue;
    const fieldRow = node("div");
    fieldRow.className = "c-field";
    fieldRow.append(node("dt", labels[field] || field.replaceAll("_", " ")), node("dd", format(field, value)));
    fields.append(fieldRow);
  }
  if (fields.childElementCount) card.append(fields);
  const flags = visit.receipt.filter(row => row.status === "present");
  for (const flag of flags) {
    const note = node("p", `${flag.label || flag.sign}: Present · Refer to PHC · ${flag.source || ""} ${flag.page || ""}`);
    note.className = "dashboard-flag";
    card.append(note);
  }
  for (const concern of visit.record.worker_concerns || []) {
    if (concern.flagged) card.append(node("p", `Worker concern for ANM: “${concern.quote}”`));
  }
  if (visit.previous_date) {
    card.append(node("h4", "Measurement changes"));
    if (!visit.changes.length) card.append(node("p", "No matching measurements to compare."));
    for (const change of visit.changes) {
      const after = format(change.field, change.after);
      const value = change.direction === "unchanged" ? after : `${format(change.field, change.before)} → ${after}`;
      const baseline = `${change.seeded_baseline ? "synthetic baseline from " : ""}${change.previous_date.slice(0, 10)}`;
      card.append(node("p", `${labels[change.field] || change.field}: ${value} · ${change.direction} compared with ${baseline}`));
    }
  } else {
    card.append(node("p", "No earlier visit of this type is available."));
  }
  const details = node("details");
  details.append(node("summary", "Danger-sign receipt"));
  const signs = node("ul");
  for (const row of visit.receipt) {
    signs.append(node("li", `${row.label || row.sign}: ${states[row.status]} ${row.quote ? '· “' + row.quote + '”' : ''}`));
  }
  details.append(signs);
  card.append(details);
  return card;
}

async function loadHistory() {
  const sequence = ++request;
  historyList.replaceChildren();
  status.textContent = "Loading visits…";
  try {
    const response = await fetch(`/api/patients/${encodeURIComponent(patients.value)}/history`);
    if (!response.ok) throw new Error();
    const visits = await response.json();
    if (sequence !== request) return;
    status.textContent = visits.length ? "" : "No visits filed for this patient yet.";
    historyList.append(...visits.map(visitCard));
    document.getElementById(location.hash.slice(1))?.scrollIntoView();
  } catch {
    if (sequence === request) status.textContent = "Could not load patient history.";
  }
}

async function loadPatients() {
  try {
    const response = await fetch("/api/beneficiaries");
    if (!response.ok) throw new Error();
    const data = await response.json();
    const list = (Array.isArray(data) ? data : data.beneficiaries || []).filter(person => person.synthetic === true);
    if (!list.length) {
      status.textContent = "No synthetic patients available.";
      return;
    }
    for (const person of list) {
      const option = node("option", person.name);
      option.value = String(person.id);
      patients.append(option);
    }
    if (list.some(person => String(person.id) === requested)) patients.value = requested;
    patients.disabled = false;
    await loadHistory();
  } catch {
    status.textContent = "Could not load synthetic patients.";
  }
}

patients.addEventListener("change", () => {
  const url = new URL(location.href);
  url.searchParams.set("patient", patients.value);
  url.hash = "";
  history.replaceState(null, "", url);
  loadHistory();
});
loadPatients();
