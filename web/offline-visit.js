"use strict";

const OfflineVisit = (() => {
  const marker = "asha-visit-draft";
  let database;

  function open() {
    if (!database) database = new Promise((resolve, reject) => {
      const request = indexedDB.open("asha-offline-visits", 1);
      request.onupgradeneeded = () => request.result.createObjectStore("drafts");
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    return database;
  }

  async function transact(mode, operation) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction("drafts", mode);
      const request = operation(transaction.objectStore("drafts"));
      transaction.oncomplete = () => resolve(request.result);
      transaction.onabort = () => reject(transaction.error);
    });
  }

  async function load() {
    const id = sessionStorage.getItem(marker);
    if (!id) return null;
    const stored = await transact("readonly", store => store.get(id));
    if (!stored) return null;
    const data = await crypto.subtle.decrypt({ name: "AES-GCM", iv: stored.iv }, stored.key, stored.data);
    return { ...JSON.parse(new TextDecoder().decode(data)), storageKey: stored.key };
  }

  async function save(visit, entries) {
    const key = visit.storageKey ?? await crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]
    );
    visit.storageKey = key;
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const data = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key,
      new TextEncoder().encode(JSON.stringify({
        id: visit.id, draftToken: visit.draftToken, details: visit.details, handsFree: visit.handsFree,
        hasDraft: visit.hasDraft, saved: visit.saved, displayType: visit.displayType,
        checklist: visit.checklist, answers: visit.answers, checked: visit.checked, entries,
      })));
    await transact("readwrite", store => store.put({ key, iv, data }, visit.id));
    sessionStorage.setItem(marker, visit.id);
  }

  async function clear(id) {
    await transact("readwrite", store => store.delete(id));
    if (sessionStorage.getItem(marker) === id) sessionStorage.removeItem(marker);
  }

  async function decode(file) {
    if (!/\.mp3$/i.test(file.name) || file.size > 12 * 1024 * 1024) {
      throw new Error("Choose an MP3 under 12 MB and up to 60 seconds long.");
    }
    const decoder = new OfflineAudioContext(1, 1, 16000);
    let audio;
    try {
      audio = await decoder.decodeAudioData(await file.arrayBuffer());
    } catch {
      throw new Error("This browser could not read that MP3.");
    }
    if (audio.duration > 60) throw new Error("Choose a recording up to 60 seconds long.");
    const renderer = new OfflineAudioContext(1, audio.length, 16000);
    const source = renderer.createBufferSource();
    source.buffer = audio;
    source.connect(renderer.destination);
    source.start();
    const samples = (await renderer.startRendering()).getChannelData(0);
    const pcm = new DataView(new ArrayBuffer(samples.length * 2));
    for (let i = 0; i < samples.length; i++) {
      const value = Math.max(-1, Math.min(1, samples[i]));
      pcm.setInt16(i * 2, value * (value < 0 ? 32768 : 32767), true);
    }
    const bytes = new Uint8Array(pcm.buffer);
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += 8192) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
    }
    return btoa(binary);
  }

  function wavBlob(frames) {
    const size = frames.reduce((total, frame) => total + frame.byteLength, 0);
    const header = new DataView(new ArrayBuffer(44));
    for (const [offset, text] of [[0, "RIFF"], [8, "WAVE"], [12, "fmt "], [36, "data"]]) {
      for (let i = 0; i < text.length; i++) header.setUint8(offset + i, text.charCodeAt(i));
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
    return new Blob([header.buffer, ...frames], { type: "audio/wav" });
  }

  function downloadRecording(entry) {
    const pcm = Uint8Array.from(atob(entry.pcm), char => char.charCodeAt(0));
    const url = URL.createObjectURL(wavBlob([pcm]));
    const link = document.createElement("a");
    link.href = url;
    link.download = entry.name.replace(/\.mp3$/i, ".wav");
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return { load, save, clear, decode, wavBlob, downloadRecording };
})();
