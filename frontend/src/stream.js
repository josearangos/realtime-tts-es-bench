// WebSocket client for WS /v1/ws/synthesize. Turns the message sequence into handler calls.
import { assertSupportedFormat, int16FromBuffer, UnsupportedFormat } from "./pcm.js";
import { START_COMMAND } from "./api.js";

export function wsUrl(baseUrl) {
  return baseUrl.replace(/\/+$/, "").replace(/^http/i, "ws") + "/v1/ws/synthesize";
}

export function openSynthesis(baseUrl, request, handlers, WebSocketImpl = globalThis.WebSocket) {
  const ws = new WebSocketImpl(wsUrl(baseUrl));
  ws.binaryType = "arraybuffer";
  let started = false;
  let pending = null; // chunk metadata waiting for its binary frame
  let sawError = false;
  let sawSummary = false;
  let cancelled = false;
  let closed = false;

  const fail = (body, closeSocket = false) => {
    if (sawError) return;
    sawError = true;
    handlers.onError?.(body);
    if (closeSocket) { try { ws.close(); } catch { /* already closed */ } }
  };

  ws.onopen = () => ws.send(JSON.stringify(request));

  ws.onmessage = (event) => {
    if (closed || sawError) return;
    const data = event.data;
    if (typeof data === "string") {
      let msg;
      try { msg = JSON.parse(data); } catch { return fail({ error: "protocol_error", message: "Unreadable message from the backend." }, true); }
      switch (msg.type) {
        case "start":
          try { assertSupportedFormat(msg); } catch (e) { return fail({ error: "unsupported_format", message: e.message }, true); }
          started = true;
          handlers.onStart?.(msg);
          break;
        case "chunk":
          pending = msg;
          break;
        case "summary":
          sawSummary = true;
          handlers.onSummary?.(msg);
          break;
        case "error": {
          const { type, ...body } = msg;
          fail(body);
          break;
        }
        default:
          break;
      }
      return;
    }
    // binary frame
    if (!pending) return fail({ error: "protocol_error", message: "Audio frame received without chunk metadata." }, true);
    const meta = pending;
    pending = null;
    let pcm;
    try { pcm = int16FromBuffer(data); } catch (e) { return fail({ error: "protocol_error", message: e.message }, true); }
    handlers.onChunk?.(meta, pcm);
  };

  ws.onclose = () => {
    if (closed) return;
    closed = true;
    if (!cancelled && !sawError && !sawSummary) {
      if (!started) {
        fail({ error: "backend_unreachable", message: `Backend not reachable. Start it with: ${START_COMMAND}`, startCommand: START_COMMAND });
      } else {
        fail({ error: "connection_lost", message: "The connection closed before the request finished." });
      }
    }
    handlers.onClose?.();
  };

  return {
    cancel() {
      if (closed) return;
      cancelled = true;
      try { if (ws.readyState === 1) ws.send(JSON.stringify({ cancel: true })); } catch { /* ignore */ }
      try { ws.close(); } catch { /* ignore */ }
    },
  };
}

export { UnsupportedFormat };
