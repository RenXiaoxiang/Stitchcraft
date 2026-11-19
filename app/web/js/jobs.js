/* Stitchcraft front-end module: SSE job streaming and cancellation.
   Uses fetch + ReadableStream so it works even where EventSource is absent or
   silently buffered; app.js falls back to polling if the stream fails. */
(function () {
  'use strict';

  var TERMINAL = ['done', 'complete', 'completed', 'success', 'succeeded', 'failed', 'error', 'cancelled', 'canceled'];

  function isTerminal(status) {
    return TERMINAL.indexOf(String(status || '').toLowerCase()) >= 0;
  }

  function follow(jobId, handlers) {
    if (!jobId || typeof fetch !== 'function') return null;
    var callbacks = handlers || {};
    var controller = typeof AbortController === 'function' ? new AbortController() : null;
    var closed = false;
    var received = false;
    var watchdog = window.setTimeout(function () {
      if (closed || received) return;
      finish();
      if (callbacks.error) callbacks.error(new Error('The live progress stream did not deliver a frame.'));
    }, 4500);

    function finish() {
      if (closed) return;
      closed = true;
      window.clearTimeout(watchdog);
      watchdog = null;
      if (controller) { try { controller.abort(); } catch (error) { /* already aborted */ } }
    }

    function deliver(payload) {
      if (closed) return;
      received = true;
      if (callbacks.update) callbacks.update(payload);
      if (isTerminal(payload && payload.status)) finish();
    }

    function consume(text) {
      var boundary = text.indexOf('\n\n');
      while (boundary >= 0) {
        var frame = text.slice(0, boundary);
        text = text.slice(boundary + 2);
        var data = [];
        frame.split('\n').forEach(function (line) {
          if (line.indexOf('data:') === 0) data.push(line.slice(5).trimStart());
        });
        if (data.length) {
          try { deliver(JSON.parse(data.join('\n'))); } catch (error) { /* malformed frame */ }
        }
        boundary = text.indexOf('\n\n');
      }
      return text;
    }

    (async function () {
      try {
        var response = await fetch('/api/jobs/' + encodeURIComponent(jobId) + '/events', {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'text/event-stream' },
          signal: controller ? controller.signal : undefined,
        });
        if (!response.ok) throw new Error('The progress stream returned HTTP ' + response.status + '.');
        if (!response.body || !response.body.getReader) throw new Error('This browser cannot stream progress.');
        var reader = response.body.getReader();
        var decoder = new TextDecoder();
        var buffer = '';
        while (!closed) {
          var chunk = await reader.read();
          if (chunk.done) break;
          buffer = consume(buffer + decoder.decode(chunk.value, { stream: true }));
        }
        if (!closed && !received) throw new Error('The progress stream ended before sending a frame.');
      } catch (error) {
        if (closed || (error && error.name === 'AbortError')) return;
        finish();
        if (callbacks.error) callbacks.error(error);
      }
    })();

    return { close: finish };
  }

  async function cancel(jobId) {
    var response = await fetch('/api/jobs/' + encodeURIComponent(jobId) + '/cancel', {
      method: 'POST',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: '{}',
    });
    var raw = await response.text();
    var data = raw ? JSON.parse(raw) : {};
    if (!response.ok) {
      var message = (data && (data.error || data.message)) || ('Request failed (HTTP ' + response.status + ').');
      throw new Error(message);
    }
    return data;
  }

  window.StitchcraftJobs = { follow: follow, cancel: cancel, isTerminal: isTerminal };
})();
