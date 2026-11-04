// Line-based link to the Arduino over Web Serial (Chrome and Edge).
//
// Lines are written one at a time. While a write is in flight only the newest pending line is
// kept, so a fast-moving hand never builds a backlog of stale levels behind the 9600-baud link.
class SerialLink {
  constructor(baudRate, onLine, onClose) {
    this.baudRate = baudRate;
    this.onLine = onLine;     // called with each received line, trimmed
    this.onClose = onClose;   // called once each time the link closes, including on unplug
    this.port = null;
    this.encoder = new TextEncoder();
  }

  get isOpen() {
    return this.port !== null;
  }

  // Shows the browser's port picker, so it must run inside a click handler.
  async open() {
    const port = await navigator.serial.requestPort();
    await port.open({ baudRate: this.baudRate });
    this.port = port;
    this.writer = port.writable.getWriter();
    this.pending = null;
    this.flushing = null;
    this.reading = this.readLines(port);
  }

  async close() {
    const port = this.port;
    if (!port) return;
    this.port = null;
    this.pending = null;
    await this.reader.cancel().catch(() => {});
    await this.reading;
    await this.flushing;
    this.writer.releaseLock();
    await port.close().catch(() => {});
    this.onClose();
  }

  sendLatest(line) {
    if (!this.port) return;
    this.pending = line;
    this.flushing ??= this.flush();
  }

  async flush() {
    try {
      while (this.pending !== null) {
        const line = this.pending;
        this.pending = null;
        await this.writer.write(this.encoder.encode(line + '\n'));
      }
    } catch {
      this.close();   // a failed write means the device is gone
    } finally {
      this.flushing = null;
    }
  }

  async readLines(port) {
    const decoder = new TextDecoder();
    let buffered = '';
    // A framing or overrun error (likely while the board resets) only replaces port.readable,
    // so reading resumes on the new stream. port.readable is null once the device is gone.
    while (this.port === port && port.readable) {
      this.reader = port.readable.getReader();
      try {
        for (;;) {
          const { value, done } = await this.reader.read();
          if (done) break;
          buffered += decoder.decode(value, { stream: true });
          const lines = buffered.split('\n');
          buffered = lines.pop();
          for (const line of lines) {
            if (line.trim()) this.onLine(line.trim());
          }
        }
      } catch {
        // Retried by the loop condition above.
      } finally {
        this.reader.releaseLock();
      }
    }
    if (this.port === port) this.close();
  }
}
