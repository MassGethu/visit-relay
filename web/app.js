"use strict";

const enable = document.querySelector("#enable-mic");
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

const maxDebugFrames = 30 * 16000 * 2 / 1024;

let session;
let activePress = null;
let stopping = false;

function reset(current, message) {
  if (session !== current) return;
  session = null;
  current.socket?.close();
  clearTimeout(current.slowTimer);
  current.player?.stop();
  current.stream?.getTracks().forEach(track => track.stop());
  if (current.context?.state !== "closed") current.context?.close().catch(() => {});
  activePress = null;
  stopping = false;
  talk.disabled = true;
  talk.setAttribute("aria-pressed", "false");
  enable.disabled = false;
  enable.hidden = false;
  endVoice.hidden = true;
  language.disabled = false;
  handsFree.disabled = false;
  talk.hidden = false;
  status.textContent = message;
}

function showDebugAudio(current) {
  const frames = current.debugFrames;
  if (!frames?.length || frames.length > maxDebugFrames) return;
  const size = frames.length * 1024;
  const header = new DataView(new ArrayBuffer(44));
  const labels = { 0: "RIFF", 8: "WAVE", 12: "fmt ", 36: "data" };
  for (const [offset, label] of Object.entries(labels)) {
    for (let i = 0; i < label.length; i++) header.setUint8(Number(offset) + i, label.charCodeAt(i));
  }
  header.setUint32(4, 36 + size, true);
  header.setUint32(16, 16, true);
  header.setUint16(20, 1, true);
  header.setUint16(22, 1, true);
  header.setUint32(24, 16000, true);
  header.setUint32(28, 32000, true);
  header.setUint16(32, 2, true);
  header.setUint16(34, 16, true);
  header.setUint32(40, size, true);
  if (debugAudio.href) URL.revokeObjectURL(debugAudio.href);
  debugAudio.href = URL.createObjectURL(new Blob([header.buffer, ...frames], { type: "audio/wav" }));
  debugAudio.textContent = `Download last turn audio (${(size / 32000).toFixed(1)} s)`;
  debugAudio.hidden = false;
}

async function connectVisit(current, lang) {
  const response = await fetch("/api/beneficiaries");
  if (!response.ok) throw new Error("Could not load the demo visit.");
  const list = await response.json();
  const person = window.Cards?.beneficiary?.() ?? (Array.isArray(list) ? list[0] : list.beneficiaries?.[0]);
  const id = person?.id ?? person?.beneficiary_id;
  if (!id) throw new Error("No synthetic beneficiary is available.");

  const url = new URL("/ws", location.href);
  url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("timing", current.id);
  if (current.handsFree) url.searchParams.set("hands_free", "1");
  const socket = new WebSocket(url);
  current.socket = socket;
  socket.binaryType = "arraybuffer";
  socket.addEventListener("close", event => {
    reset(current, event.code === 1011 && event.reason
      ? event.reason : "Speech connection closed. Enable the microphone to try again.");
  });
  socket.addEventListener("message", ({ data }) => {
    if (session !== current) return;
    if (typeof data !== "string") {
      if (!current.muted) {
        clearTimeout(current.slowTimer);
        current.player.push(data);
      }
      return;
    }
    const event = JSON.parse(data);
    if (event.type === "speaking") {
      current.speaking = event.on;
      if (current.handsFree && event.on) current.mic.port.postMessage("pause");
      if (event.on && activePress === null && !stopping) {
        current.muted = false;
        current.audioTurn = current.disclosureStarted ? current.released : null;
        current.disclosureStarted = true;
        current.player.start();
        selectTranscript(replyTab);
        status.textContent = current.handsFree ? "Speaking. Listening will resume." : "Speaking. Hold to interrupt.";
      } else if (!event.on && !current.muted) {
        current.player.finish();
        if (!current.handsFree && activePress === null && !stopping) status.textContent = "Hold to talk.";
      }
    } else if (event.type === "transcript") {
      if (current.turn > 1) clearTimeout(current.slowTimer);
      appendTranscript(transcript, event.text);
      if (current.handsFree && current.followNextSpeech) {
        current.followNextSpeech = false;
        selectTranscript(speechTab);
      }
      if (!current.handsFree && activePress === null && !current.interrupted) status.textContent = "Ready to talk.";
    } else if (event.type === "assistant_transcript") {
      appendTranscript(assistantTranscript, event.text);
    } else if (event.type === "latency") {
      if (!current.released?.played) latency.textContent = `Prisma latency · ${Math.round(event.ms)} ms`;
    }
    window.Cards?.handle(event);
  });
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("close", reject, { once: true });
  });
  socket.send(JSON.stringify({
    type: "start_visit", beneficiary_id: String(id), visit_type: person.visit_type || "anc", lang,
  }));
}

enable.addEventListener("click", async () => {
  if (session) return;
  if (!navigator.mediaDevices?.getUserMedia || !window.AudioContext) {
    status.textContent = "Open this page over HTTPS in a browser with microphone access.";
    return;
  }
  const current = { id: crypto.randomUUID(), handsFree: handsFree.checked, turn: 0 };
  session = current;
  for (const [panel, placeholder] of [[transcript, "Your words will appear here."],
    [assistantTranscript, "AI replies will appear here."]]) {
    delete panel.dataset.hasTranscript;
    panel.textContent = placeholder;
  }
  selectTranscript(speechTab);
  enable.disabled = true;
  language.disabled = true;
  handsFree.disabled = true;
  status.textContent = "Opening microphone…";
  try {
    const context = new AudioContext();
    current.context = context;
    current.player = new VisitAudioPlayer(context, () => {
      if (session === current && current.handsFree && !current.speaking) {
        current.followNextSpeech = true;
        current.mic.port.postMessage("resume");
        status.textContent = "Listening hands-free…";
      }
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
      if (session !== current || current.socket?.readyState !== WebSocket.OPEN) return;
      if (data === "commit") {
        current.socket.send(JSON.stringify({ type: "commit" }));
        stopping = false;
        status.textContent = current.interrupted
          ? "The browser interrupted this hold. Try again."
          : "Audio sent. Hold to talk again.";
        if (captureDebugAudio) showDebugAudio(current);
      } else {
        current.socket.send(data);
        if (current.debugFrames?.length <= maxDebugFrames) current.debugFrames.push(data);
      }
    };
    mic.addEventListener("processorerror", () => {
      reset(current, "Audio capture failed. Enable the microphone to try again.");
    });
    await connectVisit(current, language.value);
    if (session !== current) return;
    input.connect(mic).connect(context.destination);
    current.stream.getAudioTracks()[0].addEventListener("ended", () => {
      reset(current, "The microphone stopped. Enable it to try again.");
    });
    latency.textContent = "Prisma latency · —";
    enable.hidden = true;
    endVoice.hidden = false;
    talk.disabled = current.handsFree;
    talk.hidden = current.handsFree;
    status.textContent = current.handsFree ? "Waiting for the AI disclosure…" : "Ready to talk.";
    if (!current.handsFree) talk.focus();
  } catch (error) {
    reset(current, error.name === "NotAllowedError"
      ? "Allow microphone access in your browser and try again."
      : "Could not start voice capture. Try again.");
  }
});

endVoice.addEventListener("click", () => {
  if (session) reset(session, "Voice session ended. Enable the microphone to start again.");
});

function startTalk(press) {
  if (!session || stopping || activePress !== null) return false;
  clearTimeout(session.slowTimer);
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
  session.mic.port.postMessage("stop");
  talk.setAttribute("aria-pressed", "false");
  status.textContent = "Sending audio…";
  const current = session;
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
window.addEventListener("pagehide", () => {
  if (session) reset(session, "Enable your microphone to start.");
});
