"use strict";

class VisitAudioPlayer {
  constructor(context, onDrain = () => {}, onStart = () => {}) {
    this.context = context;
    this.onDrain = onDrain;
    this.onStart = onStart;
    this.batch = null;
  }

  start() {
    if (this.batch && !this.batch.ended) this.stop();
    const gain = this.context.createGain();
    gain.connect(this.context.destination);
    this.batch = { gain, pending: [], samples: 0, next: 0, sources: new Set(), ended: false };
  }

  push(bytes) {
    const batch = this.batch;
    if (!batch || batch.ended) return;
    const input = new DataView(bytes);
    const pcm = new Float32Array(Math.floor(input.byteLength / 2));
    for (let i = 0; i < pcm.length; i++) pcm[i] = input.getInt16(i * 2, true) / 32768;
    batch.pending.push(pcm);
    batch.samples += pcm.length;
    if (batch.next || batch.samples >= 1920) this.flush(batch);
  }

  flush(batch) {
    if (!batch.samples) return;
    const buffer = this.context.createBuffer(1, batch.samples, 24000);
    let offset = 0;
    for (const pcm of batch.pending) {
      buffer.copyToChannel(pcm, 0, offset);
      offset += pcm.length;
    }
    batch.pending = [];
    batch.samples = 0;
    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(batch.gain);
    source.onended = () => {
      batch.sources.delete(source);
      if (!batch.sources.size && batch.ended) {
        batch.gain.disconnect();
        if (this.batch === batch) this.onDrain();
      }
    };
    batch.sources.add(source);
    const initial = !batch.next;
    batch.next = Math.max(batch.next, this.context.currentTime + 0.005);
    if (initial) {
      const output = this.context.getOutputTimestamp?.();
      const delay = output?.performanceTime > 0
        ? output.performanceTime + (batch.next - output.contextTime) * 1000 - performance.now()
        : (batch.next - this.context.currentTime + (this.context.outputLatency || 0)) * 1000;
      batch.startTimer = setTimeout(() => {
        if (this.batch === batch) this.onStart(performance.now());
      }, Math.max(0, delay));
    }
    source.start(batch.next);
    batch.next += buffer.duration;
  }

  finish() {
    if (!this.batch) return;
    this.flush(this.batch);
    this.batch.ended = true;
    if (!this.batch.sources.size) {
      this.batch.gain.disconnect();
      this.onDrain();
    }
  }

  stop() {
    const batch = this.batch;
    if (!batch) return;
    this.batch = null;
    clearTimeout(batch.startTimer);
    batch.ended = true;
    const now = this.context.currentTime;
    batch.gain.gain.setValueAtTime(1, now);
    batch.gain.gain.linearRampToValueAtTime(0, now + 0.015);
    for (const source of batch.sources) source.stop(now + 0.015);
    if (!batch.sources.size) batch.gain.disconnect();
  }

  get playing() {
    return Boolean(this.batch && (!this.batch.ended || this.batch.sources.size));
  }
}
