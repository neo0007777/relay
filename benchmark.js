/* benchmark.js — Chart.js benchmark dashboard for Relay */

(function () {
  const PALETTE = {
    relay:   { bg: 'rgba(59,130,246,0.75)',   border: '#3b82f6' },
    trunc:   { bg: 'rgba(245,158,11,0.65)',   border: '#f59e0b' },
    nolimit: { bg: 'rgba(100,116,139,0.45)',  border: '#64748b' },
  };

  /* ── Data ─────────────────────────────────────────── */
  const TASKS = [
    'Refactor Auth Module',
    'Implement OAuth Flow',
    'Fix Memory Leak',
    'Add Unit Tests',
    'DB Migration',
    'API Rate Limiting',
  ];

  const COMPLETION_DATA = {
    relay:   [89, 84, 91, 87, 82, 88],
    trunc:   [41, 38, 52, 45, 36, 43],
    nolimit: [96, 93, 97, 95, 91, 95],
  };

  const CONTINUITY_DATA = {
    relay:   [0.81, 0.78, 0.85, 0.80, 0.76, 0.83],
    trunc:   [0.23, 0.19, 0.30, 0.26, 0.17, 0.22],
    nolimit: [1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
  };

  /* ── Chart defaults ───────────────────────────────── */
  Chart.defaults.color      = '#8892b0';
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
  Chart.defaults.font.size   = 12;

  const gridColor = 'rgba(255,255,255,0.05)';
  const tickColor = '#4a5568';

  function makeScales(yLabel, max, stepSize) {
    return {
      x: {
        grid: { color: gridColor },
        ticks: { color: tickColor, maxRotation: 30 },
      },
      y: {
        grid: { color: gridColor },
        ticks: { color: tickColor },
        title: { display: true, text: yLabel, color: tickColor, font: { size: 11 } },
        min: 0,
        max,
        ticks: { stepSize },
      },
    };
  }

  /* ── Task Completion Chart ───────────────────────── */
  const ctxCompletion = document.getElementById('chartCompletion');
  if (ctxCompletion) {
    new Chart(ctxCompletion, {
      type: 'bar',
      data: {
        labels: TASKS,
        datasets: [
          {
            label: 'Relay',
            data: COMPLETION_DATA.relay,
            backgroundColor: PALETTE.relay.bg,
            borderColor: PALETTE.relay.border,
            borderWidth: 2,
            borderRadius: 6,
          },
          {
            label: 'Naive Truncation',
            data: COMPLETION_DATA.trunc,
            backgroundColor: PALETTE.trunc.bg,
            borderColor: PALETTE.trunc.border,
            borderWidth: 2,
            borderRadius: 6,
          },
          {
            label: 'No-Limit Baseline',
            data: COMPLETION_DATA.nolimit,
            backgroundColor: PALETTE.nolimit.bg,
            borderColor: PALETTE.nolimit.border,
            borderWidth: 2,
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: '#8892b0',
              usePointStyle: true,
              pointStyleWidth: 16,
              padding: 20,
              font: { size: 11 },
            },
          },
          tooltip: {
            backgroundColor: 'rgba(10,14,26,0.95)',
            borderColor: 'rgba(59,130,246,0.3)',
            borderWidth: 1,
            callbacks: {
              label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y}%`,
            },
          },
        },
        scales: makeScales('Task Completion (%)', 100, 20),
      },
    });
  }

  /* ── Continuity Radar Chart ──────────────────────── */
  const ctxContinuity = document.getElementById('chartContinuity');
  if (ctxContinuity) {
    new Chart(ctxContinuity, {
      type: 'radar',
      data: {
        labels: ['Goal\nRetention', 'Decision\nCarryover', 'No Dup.\nWork', 'Context\nAccuracy', 'Task\nCompleteness', 'Token\nEfficiency'],
        datasets: [
          {
            label: 'Relay',
            data: [0.82, 0.79, 0.88, 0.85, 0.87, 0.91],
            backgroundColor: 'rgba(59,130,246,0.15)',
            borderColor: '#3b82f6',
            borderWidth: 2,
            pointBackgroundColor: '#3b82f6',
            pointRadius: 4,
          },
          {
            label: 'Naive Truncation',
            data: [0.24, 0.18, 0.31, 0.22, 0.40, 0.55],
            backgroundColor: 'rgba(245,158,11,0.12)',
            borderColor: '#f59e0b',
            borderWidth: 2,
            pointBackgroundColor: '#f59e0b',
            pointRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#8892b0', usePointStyle: true, pointStyleWidth: 14, font: { size: 11 } },
          },
          tooltip: {
            backgroundColor: 'rgba(10,14,26,0.95)',
            borderColor: 'rgba(59,130,246,0.3)',
            borderWidth: 1,
          },
        },
        scales: {
          r: {
            min: 0, max: 1,
            grid: { color: 'rgba(255,255,255,0.05)' },
            angleLines: { color: 'rgba(255,255,255,0.05)' },
            ticks: { display: false, stepSize: 0.2 },
            pointLabels: {
              color: '#8892b0',
              font: { size: 10, family: "'Inter', system-ui" },
            },
          },
        },
      },
    });
  }
})();
