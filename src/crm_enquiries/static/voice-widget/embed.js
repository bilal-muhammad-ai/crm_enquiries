(function () {
  if (document.getElementById("gf-voice-widget-root")) return;

  const script = document.currentScript;
  const baseUrl = script && script.src ? new URL(script.src).origin : window.location.origin;

  const root = document.createElement("div");
  root.id = "gf-voice-widget-root";

  const launcher = document.createElement("button");
  launcher.className = "gf-voice-launcher";
  launcher.type = "button";
  launcher.setAttribute("aria-label", "Open voice FAQ");
  launcher.textContent = "🎤";

  const frameWrap = document.createElement("div");
  frameWrap.className = "gf-voice-frame-wrap";

  const iframe = document.createElement("iframe");
  iframe.src = `${baseUrl}/voice?embed=1`;
  iframe.title = "Glancy Fawcett Voice FAQ";

  frameWrap.appendChild(iframe);
  root.appendChild(frameWrap);
  root.appendChild(launcher);
  document.body.appendChild(root);

  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = `${baseUrl}/static/voice-widget/widget.css`;
  document.head.appendChild(link);

  launcher.addEventListener("click", () => {
    frameWrap.classList.toggle("open");
  });
})();
