/**
 * exam.js — Timer, submission, attempt tracking, and UI logic for exam page.
 * Configuration injected by template via window.EXAM_CONFIG
 */

(function () {
  "use strict";

  const cfg = window.EXAM_CONFIG;

  // ── DOM refs ─────────────────────────────────────────────────
  const timerDisplay  = document.getElementById("timer-display");
  const timerBox      = document.getElementById("timer-box");
  const submitBtn     = document.getElementById("submit-btn");
  const submitText    = document.getElementById("submit-text");
  const codeEditor    = document.getElementById("code-editor");
  const clearBtn      = document.getElementById("clear-btn");
  const attemptsText  = document.getElementById("attempts-text");
  const pips          = document.querySelectorAll(".pip");

  const resultCorrect = document.getElementById("result-correct");
  const resultWrong   = document.getElementById("result-wrong");
  const resultExpired = document.getElementById("result-expired");
  const scoreDisplay  = document.getElementById("score-display");
  const expectedOut   = document.getElementById("expected-output-text");
  const wrongMsg      = document.getElementById("wrong-message");
  const nextBtn       = document.getElementById("next-question-btn");

  // ── State ────────────────────────────────────────────────────
  let secondsLeft    = cfg.timeLimit;
  let secondsElapsed = 0;
  let timerInterval  = null;
  let attemptsUsed   = cfg.attemptsUsed;
  let submitted      = false;
  let timeExpired    = false;

  // ── Timer ────────────────────────────────────────────────────
  function formatTime(s) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  }

  function updateTimerColor() {
    const pct = secondsLeft / cfg.timeLimit;
    timerBox.classList.remove("timer--warn", "timer--danger");
    if (pct <= 0.15) {
      timerBox.classList.add("timer--danger");
      timerDisplay.style.color = "#f85149";
    } else if (pct <= 0.40) {
      timerBox.classList.add("timer--warn");
      timerDisplay.style.color = "#e3b341";
    } else {
      timerDisplay.style.color = "#39d353";
    }
  }

  function startTimer() {
    updateTimerColor();
    timerInterval = setInterval(() => {
      secondsLeft--;
      secondsElapsed++;
      timerDisplay.textContent = formatTime(secondsLeft);
      updateTimerColor();

      if (secondsLeft <= 0) {
        clearInterval(timerInterval);
        timeExpired = true;
        submitBtn.disabled = true;
        codeEditor.readOnly = true;
        hideResults();
        resultExpired.style.display = "flex";
        setTimeout(() => {
          window.location.href = cfg.nextUrl;
        }, 3000);
      }
    }, 1000);
  }

  // ── Attempt Pips ─────────────────────────────────────────────
  function updatePips(used) {
    pips.forEach((pip, i) => {
      pip.classList.remove("pip--used", "pip--correct");
      if (i < used) pip.classList.add("pip--used");
    });
    attemptsText.textContent = `${used}/${cfg.maxAttempts}`;
  }

  // ── Result display ────────────────────────────────────────────
  function hideResults() {
    resultCorrect.style.display = "none";
    resultWrong.style.display   = "none";
    resultExpired.style.display = "none";
  }

  // ── Submit ────────────────────────────────────────────────────
  async function handleSubmit() {
    if (submitted || timeExpired) return;

    const code = codeEditor.value;
    if (!code.trim()) { alert("Please enter your code before submitting."); return; }

    submitBtn.disabled = true;
    submitText.textContent = "Checking...";
    hideResults();

    const body = {
      problem_id: cfg.problemId,
      lang_id:    cfg.langId,
      code:       code,
      time_taken: secondsElapsed,
    };

    try {
      const res  = await fetch(cfg.submitUrl, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(body),
      });
      const data = await res.json();

      submitBtn.disabled = false;
      submitText.textContent = "Submit Answer";

      if (data.status === "correct") {
        submitted = true;
        clearInterval(timerInterval);

        // Mark last pip green
        if (pips[attemptsUsed]) {
          pips[attemptsUsed].classList.add("pip--correct");
          pips[attemptsUsed].classList.remove("pip--used");
        }

        scoreDisplay.textContent = ` — Score: ${data.score} pts`;
        expectedOut.textContent  = data.expected_output;
        resultCorrect.style.display = "flex";
        submitBtn.disabled = true;
        codeEditor.readOnly = true;

      } else if (data.status === "wrong") {
        attemptsUsed++;
        updatePips(attemptsUsed);
        wrongMsg.textContent = `${data.attempts_left} attempt${data.attempts_left !== 1 ? "s" : ""} remaining.`;
        resultWrong.style.display = "flex";

      } else if (data.status === "max_attempts") {
        hideResults();
        resultWrong.style.display = "flex";
        wrongMsg.textContent = "Maximum attempts reached.";
        submitBtn.disabled = true;
        setTimeout(() => { window.location.href = cfg.nextUrl; }, 2500);

      } else if (data.status === "already_solved") {
        window.location.href = cfg.nextUrl;
      }

    } catch (err) {
      console.error("Submission error:", err);
      submitBtn.disabled = false;
      submitText.textContent = "Submit Answer";
      alert("Network error. Please try again.");
    }
  }

  // ── Next Question ─────────────────────────────────────────────
  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      window.location.href = cfg.nextUrl;
    });
  }

  // ── Clear editor ──────────────────────────────────────────────
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (confirm("Clear editor?")) codeEditor.value = "";
    });
  }

  // ── Tab key in editor ─────────────────────────────────────────
  codeEditor.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const s   = codeEditor.selectionStart;
      const end = codeEditor.selectionEnd;
      codeEditor.value = codeEditor.value.substring(0, s) + "    " + codeEditor.value.substring(end);
      codeEditor.selectionStart = codeEditor.selectionEnd = s + 4;
    }

    // Ctrl+Enter → submit
    if (e.ctrlKey && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  });

  // ── Submit button ─────────────────────────────────────────────
  submitBtn.addEventListener("click", handleSubmit);

  // ── Init ──────────────────────────────────────────────────────
  updatePips(attemptsUsed);
  startTimer();

})();
