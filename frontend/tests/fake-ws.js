// Scripted WebSocket double. Tests drive it with open(), serverText(), serverBinary(), serverClose().
export class FakeWebSocket {
  static instances = [];
  constructor(url) {
    this.url = url;
    this.sent = [];
    this.readyState = 0;
    this.binaryType = "blob";
    this.closedByClient = false;
    this.onopen = this.onmessage = this.onclose = this.onerror = null;
    FakeWebSocket.instances.push(this);
  }
  send(data) { this.sent.push(data); }
  close() {
    if (this.readyState === 3) return;
    this.closedByClient = true;
    this.readyState = 3;
    this.onclose?.({ code: 1000 });
  }
  // --- test controls ---
  open() { this.readyState = 1; this.onopen?.({}); }
  failToOpen() { this.readyState = 3; this.onerror?.({}); this.onclose?.({ code: 1006 }); }
  serverText(obj) { this.onmessage?.({ data: typeof obj === "string" ? obj : JSON.stringify(obj) }); }
  serverBinary(int16OrBytes) {
    const bytes = int16OrBytes instanceof Int16Array
      ? new Uint8Array(int16OrBytes.buffer.slice(int16OrBytes.byteOffset, int16OrBytes.byteOffset + int16OrBytes.byteLength))
      : int16OrBytes;
    this.onmessage?.({ data: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) });
  }
  serverClose() { if (this.readyState !== 3) { this.readyState = 3; this.onclose?.({ code: 1000 }); } }
  get sentJson() { return this.sent.map((s) => JSON.parse(s)); }
  static reset() { FakeWebSocket.instances = []; }
}
