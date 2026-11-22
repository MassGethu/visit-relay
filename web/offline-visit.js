"use strict";

const OfflineVisit = (() => {
  const marker = "asha-visit-draft";
  let database;

  // localStorage survives the tab being closed or killed; sessionStorage did not.
  function remembered() {
    try { return localStorage.getItem(marker); } catch { return null; }
  }

  function remember(id) {
    try {
      if (id) localStorage.setItem(marker, id);
      else localStorage.removeItem(marker);
    } catch {
      // The IndexedDB scan in load() still finds the draft.
    }
  }

  function open() {
    if (!database) database = new Promise((resolve, reject) => {
      const request = indexedDB.open("asha-offline-visits", 2);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains("drafts")) db.createObjectStore("drafts");
        if (!db.objectStoreNames.contains("audio")) db.createObjectStore("audio");
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    // Ask the browser not to evict drafts when the phone is low on space.
    navigator.storage?.persist?.().catch(() => {});
    return database;
  }

  async function transact(stores, mode, operation) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(stores, mode);
      const request = operation(transaction);
      transaction.oncomplete = () => resolve(request?.result);
      transaction.onabort = () => reject(transaction.error);
    });
  }

  const audioRange = id => IDBKeyRange.bound(`${id}/`, `${id}/￿`);

  function toBase64(bytes) {
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += 8192) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
    }
    return btoa(binary);
  }

  async function decrypt(key, stored) {
    return crypto.subtle.decrypt({ name: "AES-GCM", iv: stored.iv }, key, stored.data);
  }

  async function encrypt(key, bytes) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    return { iv, data: await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, bytes) };
  }

  // The newest unfinished draft, so a visit is found even from a new tab.
  async function newest() {
    const all = await transact("drafts", "readonly", tx => tx.objectStore("drafts").getAll());
    const keys = await transact("drafts", "readonly", tx => tx.objectStore("drafts").getAllKeys());
    let best = null;
    all.forEach((stored, index) => {
      if (!best || (stored.savedAt ?? 0) > (best.stored.savedAt ?? 0)) best = { id: keys[index], stored };
    });
    return best;
  }

  async function load() {
    const id = remembered();
    let found = id && { id, stored: await transact("drafts", "readonly", tx => tx.objectStore("drafts").get(id)) };
    if (!found?.stored) found = await newest();
    if (!found?.stored) return null;
    const { stored } = found;
    const visit = JSON.parse(new TextDecoder().decode(await decrypt(stored.key, stored)));
    const audio = await transact("audio", "readonly", tx => tx.objectStore("audio").getAll(audioRange(visit.id)));
    const audioKeys = await transact("audio", "readonly", tx => tx.objectStore("audio").getAllKeys(audioRange(visit.id)));
    const clips = new Map();
    for (let i = 0; i < audio.length; i++) {
      clips.set(audioKeys[i].slice(visit.id.length + 1), toBase64(new Uint8Array(await decrypt(stored.key, audio[i]))));
    }
    visit.entries = (visit.entries ?? []).map(entry => entry.kind === "audio" && !entry.pcm
      ? { ...entry, pcm: clips.get(entry.id) } : entry).filter(entry => entry.kind !== "audio" || entry.pcm);
    remember(visit.id);
    return { ...visit, storageKey: stored.key, storedAudio: new Set(clips.keys()) };
  }

  async function save(visit, entries) {
    const key = visit.storageKey ?? await crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]
    );
    visit.storageKey = key;
    visit.storedAudio ??= new Set();
    // Recordings are encrypted and written once, in their own records, so
    // the frequent small saves below never rewrite megabytes of audio.
    const clips = entries.filter(entry => entry.kind === "audio");
    const fresh = [];
    for (const entry of clips.filter(clip => !visit.storedAudio.has(clip.id))) {
      const bytes = Uint8Array.from(atob(entry.pcm), char => char.charCodeAt(0));
      fresh.push([entry.id, await encrypt(key, bytes)]);
    }
    const kept = new Set(clips.map(clip => clip.id));
    const gone = [...visit.storedAudio].filter(id => !kept.has(id));
    const record = await encrypt(key, new TextEncoder().encode(JSON.stringify({
      id: visit.id, draftToken: visit.draftToken, details: visit.details, handsFree: visit.handsFree,
      hasDraft: visit.hasDraft, hasNotes: visit.hasNotes, saved: visit.saved, displayType: visit.displayType,
      checklist: visit.checklist, heard: visit.heard,
      entries: entries.map(entry => entry.kind === "audio" ? { ...entry, pcm: undefined } : entry),
    })));
    await transact(["drafts", "audio"], "readwrite", tx => {
      const audioStore = tx.objectStore("audio");
      for (const [id, clip] of fresh) audioStore.put(clip, `${visit.id}/${id}`);
      for (const id of gone) audioStore.delete(`${visit.id}/${id}`);
      return tx.objectStore("drafts").put({ key, ...record, savedAt: Date.now() }, visit.id);
    });
    for (const [id] of fresh) visit.storedAudio.add(id);
    for (const id of gone) visit.storedAudio.delete(id);
    remember(visit.id);
  }

  async function clear(id) {
    await transact(["drafts", "audio"], "readwrite", tx => {
      tx.objectStore("audio").delete(audioRange(id));
      return tx.objectStore("drafts").delete(id);
    });
    if (remembered() === id) remember(null);
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
    return toBase64(new Uint8Array(pcm.buffer));
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
