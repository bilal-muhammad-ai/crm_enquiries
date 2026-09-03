(function () {
  const params = new URLSearchParams(window.location.search);
  if (params.get("embed") === "1") {
    document.body.classList.add("embed-mode");
  }

  const messagesEl = document.getElementById("voice-messages");
  const micBtn = document.getElementById("mic-btn");
  const micLabel = document.getElementById("mic-label");
  const statusEl = document.getElementById("status");
  const textForm = document.getElementById("text-form");
  const textInput = document.getElementById("text-input");

  let ws = null;
  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;
  let busy = false;

  function wsUrl() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}/api/v1/voice/chat`;
  }

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function setBusy(value) {
    busy = value;
    micBtn.disabled = value;
    textForm.querySelector("button").disabled = value;
    textInput.disabled = value;
  }

  function addMessage(role, text) {
    const el = document.createElement("div");
    el.className = `message ${role}`;
    el.textContent = text;
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function playAudio(base64Audio) {
    if (!base64Audio) return;
    const audio = new Audio(`data:audio/mpeg;base64,${base64Audio}`);
    audio.play().catch(() => {
      setStatus("Reply ready (audio playback blocked — click mic to continue).");
    });
  }

  function connect() {
    ws = new WebSocket(wsUrl());

    ws.onopen = () => setStatus("Connected. Hold the mic button to ask a question.");

    ws.onclose = () => {
      setStatus("Disconnected. Reconnecting...");
      setTimeout(connect, 2000);
    };

    ws.onerror = () => setStatus("Connection error.");

    ws.onmessage = (event) => {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }

      if (payload.type === "session") {
        addMessage("system", payload.message || "Session started.");
        return;
      }

      if (payload.type === "transcript") {
        addMessage("user", payload.data);
        setStatus("Thinking...");
        return;
      }

      if (payload.type === "reply") {
        addMessage("assistant", payload.text);
        playAudio(payload.audio);
        setStatus("Hold the mic button to ask another question.");
        setBusy(false);
        return;
      }

      if (payload.type === "error") {
        addMessage("system", payload.message || "Something went wrong.");
        setStatus(payload.message || "Error");
        setBusy(false);
      }
    };
  }

  function sendText(text) {
    if (!ws || ws.readyState !== WebSocket.OPEN || !text.trim()) return;
    setBusy(true);
    ws.send(JSON.stringify({ type: "text", data: text.trim() }));
  }

  async function startRecording() {
    if (isRecording || busy) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks = [];
      mediaRecorder = new MediaRecorder(stream, { mimeType: getSupportedMimeType() });

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        sendAudio(blob);
      };

      mediaRecorder.start();
      isRecording = true;
      micBtn.classList.add("recording");
      micLabel.textContent = "Release to send";
      setStatus("Listening...");
    } catch {
      setStatus("Microphone access denied. Use the text input below.");
    }
  }

  function stopRecording() {
    if (!isRecording || !mediaRecorder) return;
    mediaRecorder.stop();
    isRecording = false;
    micBtn.classList.remove("recording");
    micLabel.textContent = "Hold to speak";
  }

  function getSupportedMimeType() {
    const types = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/mp4",
    ];
    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) return type;
    }
    return "";
  }

  function sendAudio(blob) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    setBusy(true);
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = String(reader.result).split(",")[1];
      const ext = blob.type.includes("ogg") ? "audio.ogg" : "audio.webm";
      ws.send(JSON.stringify({ type: "audio", data: base64, filename: ext }));
    };
    reader.readAsDataURL(blob);
  }

  micBtn.addEventListener("mousedown", startRecording);
  micBtn.addEventListener("mouseup", stopRecording);
  micBtn.addEventListener("mouseleave", stopRecording);
  micBtn.addEventListener("touchstart", (e) => {
    e.preventDefault();
    startRecording();
  });
  micBtn.addEventListener("touchend", (e) => {
    e.preventDefault();
    stopRecording();
  });

  textForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = textInput.value;
    if (!text.trim()) return;
    sendText(text);
    textInput.value = "";
  });

  connect();
})();
