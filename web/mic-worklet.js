// Average source samples over each 16 kHz interval, including fractional boundaries.
class VisitMicrophone extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / 16000;
    this.remaining = this.ratio;
    this.sum = 0;
    this.frame = new DataView(new ArrayBuffer(1024));
    this.offset = 0;
    this.history = [];
    this.recording = false;

    this.port.onmessage = ({ data }) => {
      if (data === "start") {
        this.recording = true;
        for (const buffer of this.history) this.send(buffer);
        this.history = [];
      } else if (data === "stop" && this.recording) {
        if (this.offset > 0) this.finishFrame();
        this.recording = false;
        this.port.postMessage("commit");
      }
    };
  }

  send(buffer) {
    this.port.postMessage(buffer, [buffer]);
  }

  finishFrame() {
    const buffer = this.frame.buffer;
    if (this.recording) {
      this.send(buffer);
    } else {
      this.history.push(buffer);
      // Four complete frames plus the frame in progress give 128–160 ms.
      if (this.history.length > 4) this.history.shift();
    }
    this.frame = new DataView(new ArrayBuffer(1024));
    this.offset = 0;
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel) return true;
    for (const sample of channel) {
      let available = 1;
      while (available >= this.remaining) {
        this.sum += sample * this.remaining;
        available -= this.remaining;
        const value = Math.max(-1, Math.min(1, this.sum / this.ratio));
        this.frame.setInt16(this.offset, value * (value < 0 ? 32768 : 32767), true);
        this.offset += 2;
        if (this.offset === 1024) this.finishFrame();
        this.remaining = this.ratio;
        this.sum = 0;
      }
      this.sum += sample * available;
      this.remaining -= available;
    }
    return true;
  }
}

registerProcessor("visit-microphone", VisitMicrophone);
