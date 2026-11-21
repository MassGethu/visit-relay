"use strict";

const enable = document.querySelector("#enable-mic");
const startTyping = document.querySelector("#start-typing");
const endVoice = document.querySelector("#end-voice");
const talk = document.querySelector("#talk");
const handsFree = document.querySelector("#hands-free");
const language = document.querySelector("#speech-language");
const status = document.querySelector("#voice-status");
const speechTab = document.querySelector("#speech-tab");
const replyTab = document.querySelector("#reply-tab");
const transcript = document.querySelector("#transcript");
const assistantTranscript = document.querySelector("#assistant-transcript");
const transcriptTabs = [speechTab, replyTab];

function selectTranscript(tab) {
  if (tab.getAttribute("aria-selected") === "true") return;
  const focusedTab = transcriptTabs.includes(document.activeElement);
  for (const item of transcriptTabs) {
    const selected = item === tab;
    item.setAttribute("aria-selected", String(selected));
    item.tabIndex = selected ? 0 : -1;
    document.getElementById(item.getAttribute("aria-controls")).hidden = !selected;
  }
  if (focusedTab) tab.focus();
}

for (const tab of transcriptTabs) {
  tab.addEventListener("click", () => selectTranscript(tab));
  tab.addEventListener("keydown", event => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const target = event.key === "Home" ? speechTab : event.key === "End" ? replyTab
      : tab === speechTab ? replyTab : speechTab;
    selectTranscript(target);
  });
}

function appendTranscript(panel, text) {
  if (!panel.dataset.hasTranscript) {
    panel.textContent = "";
    panel.dataset.hasTranscript = "true";
  }
  panel.append(document.createTextNode((panel.textContent ? "\n" : "") + text));
}
const latency = document.querySelector("#latency");

const debugAudio = document.querySelector("#debug-audio");
const captureDebugAudio = new URLSearchParams(location.search).get("debug") === "1";
function sendTiming(current, turn, stage, time) {
  const payload = JSON.stringify({ session: current.id, turn, stage, timestamp_ms: performance.timeOrigin + time });
  fetch("/api/latency", { method: "POST", headers: { "Content-Type": "application/json" },
    body: payload, keepalive: true }).catch(() => {});
}

const releaseTailMs = 120;
const transcriptWaitMs = 5500;
const maxDebugFrames = 30 * 16000 * 2 / 1024;
const connectionTimeoutMs = 25000;

let session;
let activePress = null;
let stopping = false;

const editor = document.querySelector("#offline-visit");
const editorStatus = document.querySelector("#offline-status");
const note = document.querySelector("#note-text");
const audioImport = document.querySelector("#offline-audio");
const questions = document.querySelector("#offline-questions");
const referral = document.querySelector("#offline-alert");
const queue = document.querySelector("#offline-queue");
const retry = document.querySelector("#retry-offline");
const confirmSave = document.querySelector("#confirm-offline");

function renderOffline(current) {
  if (session !== current) return;
  editor.hidden = false;
  const pending = current.entries.length;
  editorStatus.textContent = current.expired
    ? "The server draft is unavailable. Unsynced entries are still on this phone."
    : current.syncError || (current.syncing ? "Syncing visit entries…"
      : pending ? `${pending} saved on this phone. They’ll sync when connected.`
        : current.connected ? "Notes and answers sync automatically."
          : "Offline. Notes, recordings, and answers will sync when connected.");
  note.disabled = audioImport.disabled = Boolean(current.saved || current.expired);
  confirmSave.disabled = Boolean(!current.connected || pending || current.saved || current.expired);
  retry.hidden = !current.syncError || !current.connected;
  questions.replaceChildren(...current.checklist.map(({ sign, text }) => {
    const row = document.createElement("fieldset");
    const title = document.createElement("legend");
    title.textContent = text.replace(/<[^>]*>/g, "");
    row.append(title);
    const existing = current.entries.find(entry => entry.sign === sign)?.answer ??
      current.checked[sign] ?? current.answers[sign];
    if (existing) {
      const answer = document.createElement("span");
      answer.textContent = typeof existing === "string" ? existing : "Answered";
      row.append(answer);
    } else {
      for (const answer of ["yes", "no", "not sure"]) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "c-button";
        button.textContent = answer[0].toUpperCase() + answer.slice(1);
        button.disabled = Boolean(current.saved || current.expired);
        button.addEventListener("click", async () => {
          row.disabled = true;
          await queueEntry(current, { kind: "answer", sign, answer });
          row.disabled = false;
        });
        row.append(button, " ");
      }
    }
    return row;
  }));
  referral.hidden = !current.entries.some(entry => entry.kind === "answer" && entry.answer === "yes");
  referral.textContent = referral.hidden ? "" : "Danger sign reported. Refer to PHC.";
  queue.replaceChildren(...current.entries.map((entry, index) => {
    const row = document.createElement("li");
    row.textContent = entry.kind === "save" ? "Confirm and save visit"
      : entry.kind === "note" ? entry.text
      : entry.kind === "audio" ? entry.name
        : `${current.checklist.find(item => item.sign === entry.sign)?.text.replace(/<[^>]*>/g, "") ?? entry.sign} ${entry.answer}`;
    if (current.expired || (index === 0 && current.syncError)) {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Remove";
      remove.addEventListener("click", async () => {
        if (!window.confirm("Remove this unsynced entry from the phone?")) return;
        try {
          await saveQueue(current, entries => entries.filter(item => item.id !== entry.id));
          current.syncError = "";
          renderOffline(current);
          syncEntries(current);
        } catch {
          editorStatus.textContent = "Could not update the phone’s saved entries.";
        }
      });
      row.append(" ", remove);
      if (entry.kind === "audio") {
        const download = document.createElement("button");
        download.type = "button";
        download.textContent = "Download recording";
        download.addEventListener("click", () => OfflineVisit.downloadRecording(entry));
        row.append(" ", download);
      }
    }
    return row;
  }));
}

function saveQueue(current, change = entries => entries) {
  const write = current.writes.catch(() => {}).then(async () => {
    const entries = change(current.entries);
    await OfflineVisit.save(current, entries);
    current.entries = entries;
  });
  current.writes = write;
  return write;
}

async function queueEntry(current, entry) {
  if (session !== current || current.saved || current.expired) return false;
  try {
    await saveQueue(current, entries => {
      if (entries.length >= 50 || (entry.kind === "audio" && entries.filter(item => item.kind === "audio").length >= 5)) {
        throw new Error("Sync the current entries before adding more.");
      }
      return [...entries, { ...entry, id: crypto.randomUUID() }];
    });
    renderOffline(current);
    syncEntries(current);
    return true;
  } catch (error) {
    editorStatus.textContent = error.message || "Could not save this entry on the phone.";
    return false;
  }
}

function syncEntries(current) {
  if (session !== current || !current.connected || current.socket?.readyState !== WebSocket.OPEN ||
      current.syncing || current.acknowledging ||
      current.syncError || activePress !== null || stopping || !current.entries.length) return;
  const entry = current.entries[0];
  current.syncing = entry.id;
  talk.disabled = true;
  current.mic?.port.postMessage("pause");
  current.socket.send(JSON.stringify({ ...entry, type: "offline_entry" }));
  // The speech service streams a 60-second import in real time.
  current.syncTimer = setTimeout(() => reconnect(current, current.socket), 105000);
  renderOffline(current);
}

async function acknowledgeEntry(current, event) {
  const entry = current.entries[0];
  if (!entry || entry.id !== event.id || current.syncing !== event.id) return;
  clearTimeout(current.syncTimer);
  current.syncing = null;
  current.acknowledging = true;
  try {
    if (event.error) current.syncError = event.error;
    else {
      if (entry.kind === "answer") current.answers[entry.sign] = entry.answer;
      await saveQueue(current, entries => entries.filter(item => item.id !== entry.id));
    }
  } catch {
    current.syncError = "Could not update the phone’s saved entries. Retry sync.";
  } finally {
    current.acknowledging = false;
  }
  renderOffline(current);
  syncEntries(current);
  if (session === current && current.connected && !current.syncing) {
    talk.disabled = !current.mic || current.handsFree || Boolean(current.entries.length);
    if (!current.speaking && !current.player?.playing) listenHandsFree(current);
  }
}

document.querySelector("#offline-note").addEventListener("submit", async event => {
  event.preventDefault();
  const text = note.value.trim();
  if (session && text && await queueEntry(session, { kind: "note", text }) && note.value.trim() === text) note.value = "";
});

audioImport.addEventListener("change", async () => {
  const current = session;
  const file = audioImport.files[0];
  if (!current || !file) return;
  audioImport.disabled = true;
  editorStatus.textContent = "Preparing the recording on this phone…";
  try {
    const pcm = await OfflineVisit.decode(file);
    await queueEntry(current, { kind: "audio", name: file.name, pcm });
  } catch (error) {
    if (session === current) editorStatus.textContent = error.message;
  } finally {
    audioImport.value = "";
    audioImport.disabled = Boolean(current.saved || current.expired);
  }
});

retry.addEventListener("click", () => {
  if (!session) return;
  session.syncError = "";
  syncEntries(session);
  renderOffline(session);
});
confirmSave.addEventListener("click", () => {
  if (session && !confirmSave.disabled) {
    confirmSave.disabled = true;
    queueEntry(session, { kind: "save" }).then(saved => {
      if (!saved && session) confirmSave.disabled = !session.connected;
    });
  }
});

function clearVoiceTimers(current) {
  clearTimeout(current.slowTimer);
  clearTimeout(current.releaseTimer);
  clearTimeout(current.transcriptTimer);
  clearTimeout(current.connectionTimer);
  clearTimeout(current.retryTimer);
  clearTimeout(current.syncTimer);
  clearInterval(current.heartbeat);
}

function reset(current, message) {
  if (session !== current) return;
  session = null;
  current.socket?.close();
  clearVoiceTimers(current);
  current.player?.stop();
  current.stream?.getTracks().forEach(track => track.stop());
  if (current.context?.state !== "closed") current.context?.close().catch(() => {});
  activePress = null;
  stopping = false;
  talk.disabled = true;
  talk.setAttribute("aria-pressed", "false");
  enable.disabled = false;
  enable.hidden = false;
  startTyping.hidden = false;
  endVoice.hidden = true;
  language.disabled = false;
  handsFree.disabled = false;
  talk.hidden = false;
  editor.hidden = true;
  status.textContent = message;
}

function showDebugAudio(current) {
  const frames = current.debugFrames;
  if (!frames?.length || frames.length > maxDebugFrames) return;
  const size = frames.length * 1024;
  if (debugAudio.href) URL.revokeObjectURL(debugAudio.href);
  debugAudio.href = URL.createObjectURL(OfflineVisit.wavBlob(frames));
  debugAudio.textContent = `Download last turn audio (${(size / 32000).toFixed(1)} s)`;
  debugAudio.hidden = false;
}

async function visitDetails(lang) {
  let person = window.Cards?.beneficiary?.();
  if (!person) {
    const response = await fetch("/api/beneficiaries");
    if (!response.ok) throw new Error("Could not load the demo visit.");
    const list = await response.json();
    person = Array.isArray(list) ? list[0] : list.beneficiaries?.[0];
  }
  const id = person?.id ?? person?.beneficiary_id;
  if (!id) throw new Error("No synthetic beneficiary is available.");
  return { beneficiary_id: String(id), visit_type: person.visit_type || "anc", lang, name: person.name };
}

function listenHandsFree(current) {
  if (!current.mic || !current.handsFree || current.syncing || current.entries.length) return;
  current.followNextSpeech = true;
  current.mic.port.postMessage("resume");
  status.textContent = "Listening hands-free…";
}

function reconnect(current, socket) {
  if (session !== current || current.socket !== socket) return;
  current.socket = null;
  current.connected = false;
  current.syncing = null;
  current.syncError = "";
  current.speaking = false;
  current.muted = true;
  current.audioTurn = current.released = null;
  clearVoiceTimers(current);
  socket.close();
  current.mic?.port.postMessage("pause");
  current.player?.stop();
  activePress = null;
  stopping = false;
  talk.disabled = true;
  talk.setAttribute("aria-pressed", "false");
  if (current.hasDraft) window.Cards?.handle({ type: "speaking", on: false });
  status.textContent = current.hasDraft
    ? "Connection lost. You can still add notes and checklist answers."
    : "Waiting for a connection…";
  renderOffline(current);
  if (navigator.onLine) {
    current.retryTimer = setTimeout(() => connectVisit(current), current.retryDelay);
    current.retryDelay = Math.min(current.retryDelay * 2, 10000);
  }
}

function connectVisit(current) {
  if (session !== current || current.expired || current.socket || !navigator.onLine) return;
  const url = new URL("/ws", location.href);
  url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("timing", current.id);
  if (current.handsFree) url.searchParams.set("hands_free", "1");
  const socket = new WebSocket(url);
  current.socket = socket;
  socket.binaryType = "arraybuffer";
  current.connectionTimer = setTimeout(() => reconnect(current, socket), connectionTimeoutMs);
  socket.addEventListener("open", () => {
    if (session !== current || current.socket !== socket) return;
    socket.send(JSON.stringify({
      ...current.details, type: current.hasDraft ? "resume_visit" : "start_visit",
      draft_token: current.draftToken, after_event: current.lastEvent,
    }));
  });
  socket.addEventListener("close", event => {
    if (session !== current || current.socket !== socket) return;
    if (event.code === 4404 || event.code === 1008 || event.code === 4403) {
      current.socket = null;
      current.connected = false;
      current.syncing = null;
      current.expired = true;
      clearVoiceTimers(current);
      current.mic?.port.postMessage("pause");
      current.player?.stop();
      talk.disabled = enable.disabled = true;
      status.textContent = event.reason || "Could not open the visit.";
      renderOffline(current);
      return;
    }
    reconnect(current, socket);
  });
  socket.addEventListener("message", ({ data }) => {
    if (session !== current || current.socket !== socket) return;
    current.lastMessageAt = performance.now();
    if (typeof data !== "string") {
      if (!current.muted) {
        clearTimeout(current.slowTimer);
        current.player?.push(data);
      }
      return;
    }
    const event = JSON.parse(data);
    if (event.type === "pong") return;
    if (event.type === "offline_synced") {
      acknowledgeEntry(current, event);
      return;
    }
    if (event.type === "visit_ready") {
      clearTimeout(current.connectionTimer);
      current.connected = current.hasDraft = true;
      current.retryDelay = 500;
      current.turn = event.turn;
      current.checklist = event.checklist ?? current.checklist;
      current.saved = event.saved;
      for (const sign of event.answered_offline ?? []) current.answers[sign] ??= true;
      saveQueue(current).catch(() => { editorStatus.textContent = "Could not save the visit on this phone."; });
      current.heartbeat = setInterval(() => {
        if (performance.now() - current.lastMessageAt > 30000) reconnect(current, socket);
        else if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "ping" }));
      }, 10000);
      talk.disabled = !current.mic || current.handsFree;
      if (event.resumed) status.textContent = "Visit restored.";
      else status.textContent = current.handsFree ? "Waiting for the AI disclosure…" : "Ready to talk.";
      if (current.handsFree && !event.speaking_next) listenHandsFree(current);
      if (current.mic && !current.handsFree && !event.resumed) talk.focus();
      renderOffline(current);
      syncEntries(current);
      return;
    }
    if (event.seq) {
      if (event.seq <= current.lastEvent) return;
      current.lastEvent = event.seq;
      current.hasDraft = true;
    }
    if (event.type === "speaking") {
      current.speaking = event.on;
      if (current.handsFree && event.on) current.mic?.port.postMessage("pause");
      if (current.player && event.on && activePress === null && !stopping) {
        current.muted = false;
        current.audioTurn = current.disclosureStarted ? current.released : null;
        current.disclosureStarted = true;
        current.player.start();
        selectTranscript(replyTab);
        status.textContent = current.handsFree ? "Speaking. Listening will resume." : "Speaking. Hold to interrupt.";
      } else if (current.player && !event.on && !current.muted) {
        current.player.finish();
        if (!current.handsFree && activePress === null && !stopping) status.textContent = "Hold to talk.";
      }
    } else if (event.type === "transcript") {
      current.heardTurn = current.turn;
      clearTimeout(current.transcriptTimer);
      if (current.turn > 1) clearTimeout(current.slowTimer);
      appendTranscript(transcript, event.text);
      if (current.handsFree && current.followNextSpeech) {
        current.followNextSpeech = false;
        selectTranscript(speechTab);
      }
      if (current.connected && !current.handsFree && activePress === null && !current.interrupted) {
        status.textContent = "Ready to talk.";
      }
    } else if (event.type === "assistant_transcript") {
      const display = window.Cards?.assistantTranscriptText?.(event.text) ?? event.text;
      if (display) appendTranscript(assistantTranscript, display);
    } else if (event.type === "latency") {
      if (!current.released?.played) latency.textContent = `Prisma latency · ${Math.round(event.ms)} ms`;
    } else if (["saved", "undo", "visit_type", "receipt"].includes(event.type)) {
      if (event.type === "visit_type") {
        current.displayType = event.visit_type;
        if (event.checklist) current.checklist = event.checklist;
      }
      if (event.type === "saved" || event.type === "undo") current.saved = event.type === "saved";
      if (event.type === "receipt") current.checked = Object.fromEntries((event.rows ?? [])
        .filter(row => row.status === "present" || row.status === "ruled_out")
        .map(row => [row.sign, row.status === "present" ? "Present" : "Ruled out"]));
      renderOffline(current);
      saveQueue(current).catch(() => { editorStatus.textContent = "Could not save the visit on this phone."; });
    }
    window.Cards?.handle(event);
  });
}

function makeSession(stored) {
  return { id: crypto.randomUUID(), draftToken: crypto.randomUUID(), handsFree: handsFree.checked,
    entries: [], answers: {}, checked: {}, checklist: [], ...stored, turn: 0, lastEvent: 0, retryDelay: 500,
    writes: Promise.resolve() };
}

function showSession(current) {
  for (const [panel, placeholder] of [[transcript, "Your words will appear here."],
    [assistantTranscript, "AI replies will appear here."]]) {
    delete panel.dataset.hasTranscript;
    panel.textContent = placeholder;
  }
  selectTranscript(speechTab);
  language.value = current.details.lang;
  handsFree.checked = current.handsFree;
  language.disabled = true;
  handsFree.disabled = true;
  window.Cards?.startSession?.(current.id, {
    id: current.details.beneficiary_id, name: current.details.name, visit_type: current.displayType ?? current.details.visit_type,
  });
  enable.disabled = false;
  enable.hidden = Boolean(current.mic);
  startTyping.hidden = true;
  endVoice.hidden = false;
  talk.hidden = current.handsFree || !current.mic;
  talk.disabled = true;
  status.textContent = navigator.onLine ? "Connecting…" : "Offline. You can still work on this visit.";
  renderOffline(current);
  connectVisit(current);
}

async function prepareSession(current) {
  current.details = await visitDetails(language.value);
  if (session !== current) return;
  showSession(current);
  saveQueue(current).catch(() => { editorStatus.textContent = "Could not save the visit on this phone."; });
}

function releaseMicrophone(current, message) {
  current.player?.stop();
  current.player = null;
  current.mic?.disconnect();
  current.mic = null;
  const stream = current.stream;
  current.stream = null;
  stream?.getTracks().forEach(track => track.stop());
  current.context?.close().catch(() => {});
  current.context = null;
  if (session !== current) return;
  talk.hidden = true;
  enable.hidden = false;
  enable.disabled = false;
  status.textContent = message;
}

startTyping.addEventListener("click", async () => {
  if (session) return;
  const current = session = makeSession();
  try {
    await prepareSession(current);
  } catch {
    reset(current, "Connect once to select a beneficiary and start the visit.");
  }
});

enable.addEventListener("click", async () => {
  if (session?.mic || session?.expired) return;
  if (!navigator.mediaDevices?.getUserMedia || !window.AudioContext) {
    status.textContent = "Microphone access requires HTTPS. You can start without a microphone.";
    return;
  }
  const current = session ??= makeSession();
  enable.disabled = true;
  status.textContent = "Opening microphone…";
  try {
    const context = new AudioContext();
    current.context = context;
    current.player = new VisitAudioPlayer(context, () => {
      if (session === current && current.connected && current.handsFree && !current.speaking) listenHandsFree(current);
    }, at => {
      const turn = current.audioTurn;
      if (!turn || turn.played || session !== current) return;
      turn.played = true;
      sendTiming(current, turn.number, "first_audio_played", at);
      latency.textContent = `First reply · ${Math.round(at - turn.at)} ms`;
    });
    await context.resume();
    current.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: false, autoGainControl: false },
    });
    const track = current.stream.getAudioTracks()[0];
    const model = await navigator.userAgentData?.getHighEntropyValues?.(["model"]).catch(() => null);
    console.info("Voice capture", { model: model?.model || "unavailable", settings: track.getSettings() });
    await context.audioWorklet.addModule("mic-worklet.js");
    const input = context.createMediaStreamSource(current.stream);
    const mic = new AudioWorkletNode(context, "visit-microphone", { channelCount: 1 });
    current.mic = mic;
    mic.port.onmessage = ({ data }) => {
      if (session !== current || !current.connected || current.syncing ||
          current.socket?.readyState !== WebSocket.OPEN) return;
      if (data === "commit") {
        current.socket.send(JSON.stringify({ type: "commit" }));
        stopping = false;
        status.textContent = current.interrupted
          ? "The browser interrupted this hold. Try again."
          : "Audio sent. Hold to talk again.";
        if (!current.interrupted && current.heardTurn !== current.turn) {
          const turn = current.turn;
          current.transcriptTimer = setTimeout(() => {
            if (session === current && current.turn === turn && current.heardTurn !== turn) {
              clearTimeout(current.slowTimer);
              status.textContent = "No speech transcribed. Hold to talk and try again.";
            }
          }, transcriptWaitMs);
        }
        if (captureDebugAudio) showDebugAudio(current);
        syncEntries(current);
      } else {
        current.socket.send(data);
        if (current.debugFrames?.length <= maxDebugFrames) current.debugFrames.push(data);
      }
    };
    mic.addEventListener("processorerror", () => {
      releaseMicrophone(current, "Audio capture failed. You can keep entering notes.");
    });
    input.connect(mic).connect(context.destination);
    current.stream.getAudioTracks()[0].addEventListener("ended", () => {
      if (current.stream) releaseMicrophone(current, "The microphone stopped. You can keep entering notes.");
    });
    latency.textContent = "Prisma latency · —";
    if (!current.details) await prepareSession(current);
    else if (session === current) {
      enable.hidden = true;
      talk.hidden = current.handsFree;
      talk.disabled = !current.connected || current.handsFree || Boolean(current.entries.length);
      status.textContent = current.connected ? "Ready to talk." : "Microphone will resume when connected.";
      if (current.connected && !current.speaking) listenHandsFree(current);
    }
  } catch (error) {
    const message = error.name === "NotAllowedError"
      ? "Allow microphone access in your browser and try again."
      : "Could not start voice capture. You can enter notes instead.";
    if (current.details) releaseMicrophone(current, message);
    else reset(current, message);
  }
});

endVoice.addEventListener("click", async () => {
  const current = session;
  if (current) {
    endVoice.disabled = true;
    try {
      await current.writes.catch(() => {});
      if (current.entries.length && !window.confirm("End the visit session and discard unsynced entries?")) return;
      await OfflineVisit.clear(current.id);
    } catch {
      editorStatus.textContent = "Could not clear the saved entries. Try again.";
      return;
    } finally {
      endVoice.disabled = false;
    }
    if (current.socket?.readyState === WebSocket.OPEN) current.socket.send(JSON.stringify({ type: "end_visit" }));
    reset(current, "Visit session ended. Start again when ready.");
    window.Cards?.endSession?.();
  }
});

function startTalk(press) {
  if (!session?.connected || !session.mic || session.entries.length ||
      session.socket?.readyState !== WebSocket.OPEN || stopping || activePress !== null) return false;
  clearTimeout(session.slowTimer);
  clearTimeout(session.transcriptTimer);
  activePress = press;
  selectTranscript(speechTab);
  session.turn++;
  session.released = null;
  if (session.speaking || session.player.playing) {
    session.muted = true;
    session.player.stop();
    session.socket.send(JSON.stringify({ type: "barge_in" }));
  }
  session.interrupted = false;
  if (captureDebugAudio) {
    session.debugFrames = [];
    debugAudio.hidden = true;
  }
  session.mic.port.postMessage("start");
  talk.setAttribute("aria-pressed", "true");
  status.textContent = "Listening…";
  return true;
}

function stopTalk(press, interrupted = false) {
  if (activePress !== press || !session) return;
  activePress = null;
  stopping = true;
  session.interrupted = interrupted;
  const at = performance.now();
  session.released = { number: session.turn, at };
  sendTiming(session, session.turn, "release", at);
  const current = session;
  // Let the capture graph deliver audio still in flight at pointer release.
  current.releaseTimer = setTimeout(() => {
    if (session === current) current.mic.port.postMessage("stop");
  }, interrupted ? 0 : releaseTailMs);
  talk.setAttribute("aria-pressed", "false");
  status.textContent = "Sending audio…";
  current.slowTimer = setTimeout(() => {
    if (session === current && !current.interrupted) status.textContent = "Slow network or reply. Still processing…";
  }, 3000);
}

talk.addEventListener("pointerdown", event => {
  if (event.button === 0 && startTalk(event.pointerId)) talk.setPointerCapture(event.pointerId);
});
for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) {
  talk.addEventListener(type, event => stopTalk(event.pointerId, type !== "pointerup"));
}
talk.addEventListener("contextmenu", event => event.preventDefault());
talk.addEventListener("keydown", event => {
  if (event.key !== " " && event.key !== "Enter") return;
  event.preventDefault();
  if (!event.repeat) startTalk(event.key);
});
talk.addEventListener("keyup", event => stopTalk(event.key));
window.addEventListener("blur", () => {
  if (activePress !== null) stopTalk(activePress, true);
});
window.addEventListener("offline", () => {
  if (session?.socket) reconnect(session, session.socket);
});
window.addEventListener("online", () => {
  if (session?.details && !session.expired) {
    clearTimeout(session.retryTimer);
    connectVisit(session);
  }
});
window.addEventListener("pagehide", () => {
  if (session) reset(session, "Enable your microphone to start.");
});

enable.disabled = startTyping.disabled = true;
OfflineVisit.load().then(stored => {
  if (stored) {
    session = makeSession(stored);
    showSession(session);
  }
}).catch(() => {
  status.textContent = "Could not restore the local visit. Check browser storage and reload.";
}).finally(() => {
  enable.disabled = startTyping.disabled = false;
});
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/visit-worker.js").catch(() => {});
