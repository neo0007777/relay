/* demo.js — Interactive context-fill → checkpoint → resume animation */

(function () {

  /* ── State ───────────────────────────────────────── */
  let animTimer    = null;
  let logTimer     = null;
  let isRunning    = false;
  let currentStep  = 0;

  /* ── DOM refs ─────────────────────────────────────── */
  const fill       = document.getElementById('ctxFill');
  const pct        = document.getElementById('ctxPct');
  const tokens     = document.getElementById('ctxTokens');
  const logWrap    = document.getElementById('agentLog');
  const cpBadge    = document.getElementById('checkpointBadge');
  const replayBtn  = document.getElementById('replayBtn');

  if (!fill) return; // guard

  /* ── Log script ────────────────────────────────────
     Each entry: [delayMs, text, className, barPct]
  ───────────────────────────────────────────────────── */
  const LOG_SCRIPT = [
    [0,    '14:21:01', 'Initializing OpenHands agent session...', 'highlight'],
    [700,  '14:21:02', 'Task: Refactor authentication module in /src/auth/', 'log-text'],
    [1400, '14:21:03', 'Reading AuthManager.ts... 847 tokens consumed', 'log-text'],
    [2100, '14:21:04', 'Reading UserSession.ts... 1,203 tokens consumed', 'log-text'],
    [2800, '14:21:06', 'Analyzing JWT validation logic... 2,418 tokens', 'log-text'],
    [3400, '14:21:09', 'Generated refactoring plan. Writing changes...', 'highlight'],
    [4000, '14:21:12', 'Edited AuthManager.ts — extracting token refresh logic', 'log-text'],
    [4700, '14:21:16', 'Reading middleware/cors.ts... 3,812 tokens total', 'log-text'],
    [5400, '14:21:21', 'Running unit tests... 3 passing, 2 failing', 'warn'],
    [6000, '14:21:24', 'Analyzing test failures... reading test fixtures...', 'log-text'],
    [6700, '14:21:29', 'Token count: 98,441 / 128,000  [76%]', 'warn'],
    [7300, '14:21:33', 'Reading TokenService.ts, RefreshQueue.ts...', 'log-text'],
    [7900, '14:21:38', 'Patching refresh token race condition...', 'log-text'],
    [8500, '14:21:42', 'Token count: 109,243 / 128,000  [85%] ⚠ THRESHOLD', 'warn'],
    [9000, '14:21:42', '╔══ RELAY CHECKPOINT TRIGGERED ══╗', 'relay'],
    [9300, '14:21:43', 'Serializing goal state and decision log...', 'relay'],
    [9800, '14:21:43', 'Compressing: summary + rejected approaches + diffs', 'relay'],
    [10300,'14:21:44', 'Retrieving context via dependency graph...', 'relay'],
    [10800,'14:21:44', 'Checkpoint saved → relay-session-7f3a.json', 'success'],
    [11400,'14:21:45', 'New agent instance initialized. Resuming...', 'success'],
    [12000,'14:21:46', '✓ Goal restored: auth module refactor in progress', 'success'],
    [12500,'14:21:46', '✓ Context: 3 decisions, 2 rejected approaches loaded', 'success'],
    [13000,'14:21:47', 'Agent resumed. Continuing from token refresh patch...', 'highlight'],
  ];

  /* ── Bar color by pct ─────────────────────────────── */
  function barColor(p) {
    if (p < 60) return 'linear-gradient(90deg, #3b82f6, #6366f1)';
    if (p < 80) return 'linear-gradient(90deg, #f59e0b, #ef4444)';
    return 'linear-gradient(90deg, #ef4444, #dc2626)';
  }

  function pctFromStep(step) {
    // maps log step index to a context percentage
    const max_step = LOG_SCRIPT.length - 1;
    const base = Math.min((step / max_step) * 105, 105);
    // reset after checkpoint (step 14+)
    if (step >= 14) return Math.max(3, Math.min(base, 88)); // freeze near 88 then reset
    return Math.min(base, 88);
  }

  function tokenCount(p) {
    return Math.round(p * 0.01 * 128000).toLocaleString();
  }

  /* ── Run a single log step ───────────────────────── */
  function runStep(i) {
    if (i >= LOG_SCRIPT.length) {
      isRunning = false;
      replayBtn.style.display = 'flex';
      return;
    }
    currentStep = i;
    const [delay, time, text, cls] = LOG_SCRIPT[i];

    logTimer = setTimeout(() => {
      // build log line
      const line = document.createElement('div');
      line.className = 'log-line';

      const timeEl = document.createElement('span');
      timeEl.className = 'log-time';
      timeEl.textContent = time;

      const textEl = document.createElement('span');
      textEl.className = `log-text ${cls}`;
      textEl.textContent = text;

      line.appendChild(timeEl);
      line.appendChild(textEl);
      logWrap.appendChild(line);

      // scroll log
      requestAnimationFrame(() => {
        logWrap.scrollTop = logWrap.scrollHeight;
        requestAnimationFrame(() => line.classList.add('visible'));
      });

      // update bar
      const p = pctFromStep(i);
      let barPct = p;

      // checkpoint trigger animation
      if (i === 14) {
        // flash the bar then show badge
        fill.style.transition = 'width 0.3s ease, background 0.3s ease';
        fill.style.width = '86%';
        fill.style.background = 'linear-gradient(90deg, #ef4444, #dc2626)';
        setTimeout(() => {
          cpBadge.classList.add('show');
          // animate bar dropping (new agent)
        }, 400);
      }

      if (i >= 18) {
        // new agent — bar resets low and climbs fresh
        const newPct = 2 + (i - 18) * 3;
        barPct = Math.min(newPct, 18);
        fill.style.background = 'linear-gradient(90deg, #3b82f6, #6366f1)';
      }

      if (i < 14) {
        fill.style.width = barPct + '%';
        fill.style.background = barColor(barPct);
        pct.textContent    = Math.round(barPct) + '%';
        tokens.textContent = tokenCount(barPct);
      } else if (i >= 18) {
        fill.style.width = barPct + '%';
        pct.textContent    = Math.round(barPct) + '%';
        tokens.textContent = tokenCount(barPct);
      }

      // next step
      const nextDelay = i + 1 < LOG_SCRIPT.length
        ? LOG_SCRIPT[i + 1][0] - LOG_SCRIPT[i][0]
        : 0;
      animTimer = setTimeout(() => runStep(i + 1), nextDelay);

    }, i === 0 ? 0 : (LOG_SCRIPT[i][0] - LOG_SCRIPT[i - 1][0]));
  }

  /* ── Start / Replay ───────────────────────────────── */
  function start() {
    if (isRunning) return;
    isRunning = true;
    currentStep = 0;

    // reset UI
    logWrap.innerHTML = '';
    cpBadge.classList.remove('show');
    replayBtn.style.display = 'none';
    fill.style.width = '0%';
    fill.style.background = barColor(0);
    fill.style.transition = 'width 0.6s ease, background 0.3s ease';
    pct.textContent = '0%';
    tokens.textContent = '0';

    clearTimeout(animTimer);
    clearTimeout(logTimer);

    // small delay before starting
    setTimeout(() => runStep(0), 400);
  }

  /* ── Auto-start on first scroll into view ─────────── */
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && !isRunning && currentStep === 0) {
        start();
        observer.disconnect();
      }
    },
    { threshold: 0.3 }
  );

  const heroSection = document.getElementById('hero');
  if (heroSection) observer.observe(heroSection);

  /* ── Replay button ────────────────────────────────── */
  if (replayBtn) {
    replayBtn.addEventListener('click', () => {
      isRunning = false;
      start();
    });
  }

  /* ── Nav scroll effect ────────────────────────────── */
  const nav = document.querySelector('nav');
  const scrollBar = document.getElementById('scroll-progress');
  const docEl = document.documentElement;

  window.addEventListener('scroll', () => {
    if (nav) {
      nav.classList.toggle('scrolled', window.scrollY > 40);
    }
    if (scrollBar) {
      const scrolled = (docEl.scrollTop / (docEl.scrollHeight - docEl.clientHeight)) * 100;
      scrollBar.style.width = scrolled + '%';
    }
  }, { passive: true });

  /* ── Scroll reveal ────────────────────────────────── */
  const revealEls = document.querySelectorAll('.reveal');
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('visible');
          revealObserver.unobserve(e.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
  );
  revealEls.forEach(el => revealObserver.observe(el));

  /* ── Pipeline step accordion ─────────────────────── */
  document.querySelectorAll('.pipeline-step').forEach(step => {
    step.addEventListener('click', () => {
      const wasActive = step.classList.contains('active');
      document.querySelectorAll('.pipeline-step').forEach(s => s.classList.remove('active'));
      if (!wasActive) step.classList.add('active');
    });
  });

  /* ── Open first pipeline step ─────────────────────── */
  const firstStep = document.querySelector('.pipeline-step');
  if (firstStep) firstStep.classList.add('active');

})();
