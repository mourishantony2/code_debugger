/**
 * security.js — Exam hardened security
 *
 * TAB SWITCH      → POST /exam/violation → immediate logout
 * FULLSCREEN EXIT → POST /exam/violation → immediate logout
 *
 * Uses ONLY visibilitychange (not window.blur) to avoid false positives
 * from address-bar focus, DevTools, or same-site tab navigation.
 */

(function () {
  "use strict";

  const isExamPage  = document.getElementById("exam-wrapper") !== null;
  const problemId   = document.querySelector('meta[name="problem-id"]')?.content || null;

  /* ─── 1. RIGHT-CLICK ────────────────────────────────────────────── */
  document.addEventListener("contextmenu", (e) => e.preventDefault());

  /* ─── 2. COPY / CUT / PASTE ─────────────────────────────────────── */
  ["copy", "cut", "paste"].forEach((ev) =>
    document.addEventListener(ev, (e) => { if (isExamPage) e.preventDefault(); })
  );

  /* ─── 3. KEYBOARD SHORTCUTS ─────────────────────────────────────── */
  document.addEventListener("keydown", (e) => {
    const k = e.key.toUpperCase();
    if (e.key === "F12") { e.preventDefault(); return; }
    if (e.ctrlKey && k === "U") { e.preventDefault(); return; }
    if (e.ctrlKey && e.shiftKey && ["I","J","C"].includes(k)) { e.preventDefault(); return; }
    if (isExamPage) {
      if (e.key === "F5" || (e.ctrlKey && k === "R")) { e.preventDefault(); return; }
      if (e.ctrlKey && k === "W")     { e.preventDefault(); return; }
      if (e.altKey  && e.key === "F4") { e.preventDefault(); return; }
      if (e.ctrlKey && e.key === "Tab") { e.preventDefault(); return; }
    }
  });

  /* ─── 4. BACK NAVIGATION PREVENTION ─────────────────────────────── */
  if (isExamPage) {
    history.pushState(null, "", location.href);
    window.addEventListener("popstate", () => history.pushState(null, "", location.href));
  }

  /* ─── 5. VIOLATION LOGGER ────────────────────────────────────────── */
  /**
   * POST to /exam/violation before logout so admin sees what happened.
   * Uses keepalive:true so the request completes even during page unload.
   */
  async function logViolationAndLogout(violationType) {
    // Show the "you're being logged out" screen immediately
    showFinalOverlay(violationType);

    try {
      await fetch("/exam/violation", {
        method:    "POST",
        headers:   { "Content-Type": "application/json" },
        keepalive: true,    // survives page navigation
        body:      JSON.stringify({
          violation_type: violationType,
          problem_id:     problemId,
        }),
      });
    } catch (_) {
      // network error — still redirect
    }

    // Short pause so the overlay is visible, then logout
    setTimeout(() => { window.location.href = "/logout"; }, 900);
  }

  /* ─── 6. TAB SWITCH → LOG + LOGOUT ──────────────────────────────── */
  if (isExamPage) {
    let ready = false;
    setTimeout(() => { ready = true; }, 1200);   // grace period for page init

    document.addEventListener("visibilitychange", () => {
      if (!ready) return;
      if (document.hidden) {
        logViolationAndLogout("tab_switch");
      }
    });
  }

  /* ─── 7. FULLSCREEN ENFORCEMENT + EXIT → LOG + LOGOUT ────────────── */
  if (isExamPage) {
    const fsOverlay = document.getElementById("fullscreen-overlay");
    const enterBtn  = document.getElementById("enter-fullscreen-btn");

    function isFS() {
      return !!(document.fullscreenElement ||
                document.webkitFullscreenElement ||
                document.mozFullScreenElement);
    }

    function requestFS() {
      const el = document.documentElement;
      if (el.requestFullscreen)       return el.requestFullscreen();
      if (el.webkitRequestFullscreen) return el.webkitRequestFullscreen();
      if (el.mozRequestFullScreen)    return el.mozRequestFullScreen();
      return Promise.resolve();
    }

    function showFSPrompt() { if (fsOverlay) fsOverlay.style.display = "flex"; }
    function hideFSPrompt() { if (fsOverlay) fsOverlay.style.display = "none"; }

    // Prompt to enter fullscreen on load
    window.addEventListener("load", () => {
      setTimeout(() => { if (!isFS()) showFSPrompt(); }, 700);
    });

    if (enterBtn) {
      enterBtn.addEventListener("click", () => requestFS().then(hideFSPrompt).catch(hideFSPrompt));
    }

    let hasBeenFS = false;

    function onFSChange() {
      if (isFS()) {
        hasBeenFS = true;
        hideFSPrompt();
      } else if (hasBeenFS) {
        // They WERE in fullscreen and left — log + logout immediately
        logViolationAndLogout("fullscreen_exit");
      }
    }

    document.addEventListener("fullscreenchange",       onFSChange);
    document.addEventListener("webkitfullscreenchange", onFSChange);
    document.addEventListener("mozfullscreenchange",    onFSChange);
  }

  /* ─── HELPER: Red "Logging out…" overlay ────────────────────────── */
  function showFinalOverlay(type) {
    const existing = document.getElementById("_exam_final_overlay");
    if (existing) return;  // already showing

    const title   = type === "tab_switch" ? "📋 Tab Switch Detected"   : "⬜ Fullscreen Exited";
    const message = type === "tab_switch"
      ? "You switched tabs during the exam. This violation has been recorded."
      : "You exited fullscreen mode. This violation has been recorded.";

    const el = document.createElement("div");
    el.id = "_exam_final_overlay";
    el.style.cssText = "position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,.97);" +
                       "display:flex;align-items:center;justify-content:center;font-family:'Inter',sans-serif";

    el.innerHTML = `
      <div style="background:#161b22;border:2px solid #f85149;border-radius:14px;
                  box-shadow:0 0 60px rgba(248,81,73,.4);max-width:430px;padding:2.5rem 2rem;
                  text-align:center;display:flex;flex-direction:column;gap:1rem;
                  animation:_elo_in .25s ease">
        <div style="font-size:3rem;line-height:1">🚨</div>
        <h2 style="color:#f85149;font-size:1.35rem;margin:0">${title}</h2>
        <p style="color:#8b949e;font-size:.9rem;margin:0;line-height:1.55">${message}</p>
        <p style="color:#e3b341;font-weight:700;font-size:.95rem;margin:0">
          Recording violation &amp; logging out…
        </p>
      </div>
      <style>
        @keyframes _elo_in {
          from{opacity:0;transform:translateY(16px)}
          to  {opacity:1;transform:translateY(0)}
        }
      </style>`;

    document.body.appendChild(el);
  }

})();
