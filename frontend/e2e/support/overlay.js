// Runs inside every page of the demo: draws the caption bar, chapter cards and a
// visible mouse pointer (browser videos do not show the real one).
(() => {
  if (window.__demoOverlayInstalled) return;
  window.__demoOverlayInstalled = true;

  const css = `
    #demo-caption { position: fixed; left: 16px; bottom: 16px; z-index: 2147483646;
      max-width: 620px; width: max-content; padding: 12px 20px; border-radius: 12px; pointer-events: none;
      background: rgba(15, 23, 42, 0.88); color: #fff; font: 500 17px/1.45 system-ui, sans-serif;
      box-shadow: 0 8px 30px rgba(0,0,0,.25); transition: opacity .2s; }
    #demo-caption b { display: block; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: #6ee7b7; margin-bottom: 2px; }
    #demo-card { position: fixed; inset: 0; z-index: 2147483647; display: flex; flex-direction: column; align-items: center;
      justify-content: center; background: linear-gradient(135deg, #0f2e2b, #136f5b); color: #fff; font-family: system-ui, sans-serif; pointer-events: none; }
    #demo-card .num { font-size: 18px; letter-spacing: .2em; text-transform: uppercase; color: #a7f3d0; }
    #demo-card .title { font-size: 54px; font-weight: 700; margin: 10px 0; }
    #demo-card .sub { font-size: 21px; color: #d1fae5; max-width: 900px; text-align: center; }
    #demo-cursor { position: fixed; z-index: 2147483647; width: 22px; height: 22px; margin: -3px 0 0 -3px; pointer-events: none;
      transition: left .12s linear, top .12s linear; }
    .demo-ripple { position: fixed; z-index: 2147483646; width: 34px; height: 34px; margin: -17px 0 0 -17px; border-radius: 50%;
      border: 3px solid #10b981; pointer-events: none; animation: demo-ripple .5s ease-out forwards; }
    @keyframes demo-ripple { from { transform: scale(.3); opacity: 1 } to { transform: scale(1.4); opacity: 0 } }
  `;
  const cursorSvg =
    '<svg viewBox="0 0 24 24" width="22" height="22"><path d="M3 2l7 19 2.5-7.5L20 11z" fill="#111" stroke="#fff" stroke-width="1.5"/></svg>';

  function ensure() {
    if (!document.body) return false;
    if (!document.getElementById("demo-style")) {
      const style = document.createElement("style");
      style.id = "demo-style";
      style.textContent = css;
      document.head.appendChild(style);
    }
    if (!document.getElementById("demo-cursor")) {
      const cursor = document.createElement("div");
      cursor.id = "demo-cursor";
      cursor.innerHTML = cursorSvg;
      const saved = JSON.parse(sessionStorage.getItem("demoCursor") || '{"x":720,"y":450}');
      cursor.style.left = saved.x + "px";
      cursor.style.top = saved.y + "px";
      document.body.appendChild(cursor);
    }
    renderCaption();
    return true;
  }

  function renderCaption() {
    const data = JSON.parse(sessionStorage.getItem("demoCaption") || "null");
    let box = document.getElementById("demo-caption");
    if (!data) {
      if (box) box.remove();
      return;
    }
    if (!box) {
      box = document.createElement("div");
      box.id = "demo-caption";
      document.body.appendChild(box);
    }
    box.innerHTML = (data.title ? "<b>" + data.title + "</b>" : "") + data.text;
  }

  window.__demoCaption = (title, text) => {
    sessionStorage.setItem("demoCaption", JSON.stringify(text ? { title, text } : null));
    ensure();
    renderCaption();
  };

  window.__demoCard = (num, title, sub) => {
    ensure();
    let card = document.getElementById("demo-card");
    if (!title) {
      if (card) card.remove();
      return;
    }
    if (!card) {
      card = document.createElement("div");
      card.id = "demo-card";
      document.body.appendChild(card);
    }
    card.innerHTML = '<div class="num">' + num + '</div><div class="title">' + title + '</div><div class="sub">' + (sub || "") + "</div>";
  };

  // True when the pointer rests where it would fade the caption out.
  window.__demoCursorNearCaption = () => {
    const box = document.getElementById("demo-caption");
    const saved = JSON.parse(sessionStorage.getItem("demoCursor") || "null");
    if (!box || !saved) return false;
    const r = box.getBoundingClientRect();
    return saved.x > r.left - 60 && saved.x < r.right + 60 && saved.y > r.top - 60 && saved.y < r.bottom + 60;
  };

  document.addEventListener(
    "mousemove",
    (event) => {
      if (!ensure()) return;
      const cursor = document.getElementById("demo-cursor");
      cursor.style.left = event.clientX + "px";
      cursor.style.top = event.clientY + "px";
      sessionStorage.setItem("demoCursor", JSON.stringify({ x: event.clientX, y: event.clientY }));
      // Fade the caption while the pointer is near it, so it never hides what is being clicked.
      const box = document.getElementById("demo-caption");
      if (box) {
        const r = box.getBoundingClientRect();
        const near = event.clientX > r.left - 60 && event.clientX < r.right + 60 && event.clientY > r.top - 60 && event.clientY < r.bottom + 60;
        box.style.opacity = near ? "0.12" : "1";
      }
    },
    true
  );
  document.addEventListener(
    "mousedown",
    (event) => {
      const ripple = document.createElement("div");
      ripple.className = "demo-ripple";
      ripple.style.left = event.clientX + "px";
      ripple.style.top = event.clientY + "px";
      document.body.appendChild(ripple);
      setTimeout(() => ripple.remove(), 600);
    },
    true
  );

  // Keep the overlay alive when the app re-renders the page.
  const keepAlive = () => ensure();
  document.addEventListener("DOMContentLoaded", keepAlive);
  window.addEventListener("load", keepAlive);
  setInterval(keepAlive, 500);
})();
