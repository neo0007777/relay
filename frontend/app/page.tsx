"use client";

import React, { useState, useEffect, useRef } from 'react';
import PlasmaWave from './components/PlasmaWave';

export default function Home() {
  const [scrolled, setScrolled] = useState(false);
  const [activeNav, setActiveNav] = useState('vision');
  const [demoProfile, setDemoProfile] = useState<'intercept' | 'ast' | 'whynot'>('intercept');
  const [copied, setCopied] = useState(false);

  // Use a Ref to store dynamic PlasmaWave props without triggering React re-renders on scroll
  const plasmaPropsRef = useRef({
    yOffset: 0,
    rotationDeg: 0,
    speed1: 0.05,
    bend1: 1,
  });

  const CMD = 'pip install relay-ai && relay run claude --project ./repo';

  const copyCmd = () => {
    navigator.clipboard.writeText(CMD);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const scrollTo = (id: string) => {
    setActiveNav(id);
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  // High-performance scroll handler without React re-renders
  useEffect(() => {
    let ticking = false;

    const handleScroll = () => {
      const scrollY = window.scrollY;

      if (!ticking) {
        window.requestAnimationFrame(() => {
          setScrolled(scrollY > 40);

          // Section tracking
          const sections = ['vision', 'algorithm', 'demo', 'ladder-sec', 'architecture', 'roadmap'];
          const scrollPos = scrollY + 250;
          for (const id of sections) {
            const el = document.getElementById(id);
            if (el) {
              const top = el.offsetTop;
              const height = el.offsetHeight;
              if (scrollPos >= top && scrollPos < top + height) {
                setActiveNav(id);
                break;
              }
            }
          }
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Optimized IntersectionObserver for scroll reveal
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target); // Unobserve once visible for maximum performance
          }
        });
      },
      { threshold: 0.1 }
    );

    const elements = document.querySelectorAll('.reveal-on-scroll');
    elements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  return (
    <>
      {/* ── PlasmaWave Background ────────────────────────────────────────── */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none', opacity: 0.85 }}>
        <PlasmaWave
          colors={["#A855F7", "#06B6D4"]}
          speed1={0.05}
          speed2={0.175}
          focalLength={0.8}
          bend1={1}
          bend2={0.5}
          dir2={1.0}
          rotationDeg={0}
        />
      </div>

      {/* ── Fixed Navigation Bar ────────────────────────────────────────── */}
      <nav className={`${scrolled ? 'scrolled' : ''} anim-land-down`}>
        <div className="brand" onClick={() => scrollTo('hero')}>
          <div className="icon">⚡</div>
          <span>relay</span>
          <span style={{ fontSize: '0.72rem', color: 'var(--faint)', marginLeft: '0.2rem' }}>v0.4.1</span>
        </div>

        <div className="links">
          <button onClick={() => scrollTo('vision')} className={activeNav === 'vision' ? 'active' : ''}>vision</button>
          <button onClick={() => scrollTo('algorithm')} className={activeNav === 'algorithm' ? 'active' : ''}>algorithm</button>
          <button onClick={() => scrollTo('demo')} className={activeNav === 'demo' ? 'active' : ''}>demo</button>
          <button onClick={() => scrollTo('ladder-sec')} className={activeNav === 'ladder-sec' ? 'active' : ''}>benchmark</button>
          <button onClick={() => scrollTo('architecture')} className={activeNav === 'architecture' ? 'active' : ''}>architecture</button>
          <button onClick={() => scrollTo('roadmap')} className={activeNav === 'roadmap' ? 'active' : ''}>roadmap</button>
          <a href="https://github.com/yourusername/relay" target="_blank" rel="noopener noreferrer" className="gh" style={{ color: 'var(--magenta)' }}>
            GitHub ↗
          </a>
        </div>
      </nav>

      {/* ── Staggered Hero Landing Section ──────────────────────────────── */}
      <header id="hero" className="hero">
        <div className="kicker anim-land-fade1">A G E N T   C O N T E X T   ·   M I D D L E W A R E</div>
        <h1 className="anim-land-scale">relay</h1>
        <div className="tag anim-land-fade2">infinite memory for autonomous coding agents</div>

        <p className="sub anim-land-fade2">
          Intercepts at <b>85% token budget</b>. Hand off context seamlessly with <b>zero dependencies</b>.
        </p>

        {/* Action Buttons */}
        <div className="cta anim-land-fade3">
          <a
            href="https://github.com/yourusername/relay"
            target="_blank"
            rel="noopener noreferrer"
            className="btn primary"
          >
            ★ Star on GitHub
          </a>
          <button onClick={() => scrollTo('demo')} className="btn">
            Quick start →
          </button>
          <button onClick={copyCmd} className="btn" style={{ fontFamily: 'var(--mono)', fontSize: '0.85rem' }}>
            {copied ? '✓ Copied' : '$ pip install relay-ai'}
          </button>
        </div>

        {/* Minimal Key Stats */}
        <div className="stats anim-land-fade3">
          <div>
            <div className="n">87.0%</div>
            <div className="l">COMPLETION</div>
          </div>
          <div>
            <div className="n">0.81</div>
            <div className="l">CONTINUITY</div>
          </div>
          <div>
            <div className="n">1.4s</div>
            <div className="l">LATENCY</div>
          </div>
          <div>
            <div className="n">91%</div>
            <div className="l">WORK SAVED</div>
          </div>
        </div>

        <div className="scrollcue">scroll</div>
      </header>

      {/* ── Main Content Sections (Scroll Reveal) ─────────────────────── */}
      <main>
        {/* ── 01: VISION ────────────────────────────────────────────────────── */}
        <section id="vision" className="reveal-on-scroll">
          <div className="snum">01 — the vision</div>
          <h2>Never lose hard-won context</h2>

          <div className="pillars">
            <div className="pillar reveal-on-scroll delay-1">
              <div className="ic">🧠</div>
              <h3>Why-NOT Memory Graph</h3>
              <p>
                Indexes rejected paths and failed hypotheses. New instances <b>never repeat dead ends</b>.
              </p>
            </div>

            <div className="pillar reveal-on-scroll delay-2">
              <div className="ic">🌳</div>
              <h3>AST Delta Indexer</h3>
              <p>
                Extracts exact structural diffs — <b>8x token reduction</b> vs raw transcripts.
              </p>
            </div>

            <div className="pillar reveal-on-scroll delay-3">
              <div className="ic">⚡</div>
              <h3>Hybrid Retrieval</h3>
              <p>
                BM25 keyword search paired with dense 1,024-dim vector graph search. Sub-50ms query time.
              </p>
            </div>
          </div>
        </section>

        {/* ── 02: ALGORITHM ─────────────────────────────────────────────────── */}
        <section id="algorithm" className="reveal-on-scroll">
          <div className="snum">02 — algorithm</div>
          <h2>Tiered Handoff Pipeline</h2>

          <div className="algo-grid">
            <div className="algo-copy reveal-on-scroll delay-1">
              <p>
                As coding agents stream tokens, Relay monitors budget limit. At 85%, execution pauses without dropping thread state.
              </p>
              <div className="jit">
                A fresh agent instance is booted with a compact 17.8k token handoff payload in under 1.4s.
              </div>
            </div>

            <div className="tierstack reveal-on-scroll delay-2">
              <div className="tlevel">
                <div className="sw" style={{ background: 'var(--magenta)' }}></div>
                <div className="tn">STAGE 1</div>
                <div className="td"><b>85% Intercept</b> · Intercepts active loop</div>
              </div>
              <div className="tlevel">
                <div className="sw" style={{ background: 'var(--cyan)' }}></div>
                <div className="tn">STAGE 2</div>
                <div className="td"><b>AST Delta Snapshot</b> · 847 node diffs</div>
              </div>
              <div className="tlevel">
                <div className="sw" style={{ background: 'var(--gold)' }}></div>
                <div className="tn">STAGE 3</div>
                <div className="td"><b>Why-NOT Graph Index</b> · 23 dead-end paths</div>
              </div>
              <div className="tlevel">
                <div className="sw" style={{ background: 'var(--green)' }}></div>
                <div className="tn">STAGE 4</div>
                <div className="td"><b>Agent B Boot</b> · 17.8k tokens</div>
              </div>
            </div>
          </div>
        </section>

        {/* ── 03: DEMO ──────────────────────────────────────────────────────── */}
        <section id="demo" className="reveal-on-scroll">
          <div className="snum">03 — demo</div>
          <h2>Live Handoff Simulation</h2>

          <div className="profiles reveal-on-scroll delay-1">
            <button
              onClick={() => setDemoProfile('intercept')}
              className={demoProfile === 'intercept' ? 'on' : ''}
            >
              ▶ Intercept Log
            </button>
            <button
              onClick={() => setDemoProfile('ast')}
              className={demoProfile === 'ast' ? 'on' : ''}
            >
              🌳 AST Delta Tree
            </button>
            <button
              onClick={() => setDemoProfile('whynot')}
              className={demoProfile === 'whynot' ? 'on' : ''}
            >
              🧠 Why-NOT Dead-Ends
            </button>
          </div>

          <div className="win reveal-on-scroll delay-2">
            <div className="bar">
              <span className="dot r"></span>
              <span className="dot y"></span>
              <span className="dot g"></span>
              <span className="ttl">relay_agent_handoff.py — interactive terminal</span>
            </div>

            <div className="term-body">
              {demoProfile === 'intercept' && (
                <>
                  <span className="banner">⚡ RELAY INTERCEPTOR v0.4.1</span>{'\n'}
                  <span className="bannertxt">[Agent A] Executing task: Refactor payment gateway &amp; handle retries...</span>{'\n'}
                  <span className="you">▲ Token Usage: 172,341 / 200,000 tokens (86.2%) — Threshold 85.0% Breached!</span>{'\n'}
                  <span className="ans">→ Intercepting execution loop. Pausing Agent A non-destructively...</span>{'\n'}
                  <span className="ans">→ Snapshotting AST node deltas across 14 modified files...</span>{'\n'}
                  <span className="ans">→ Indexing 23 Why-NOT dead-end memory paths...</span>{'\n'}
                  <span className="statline">✓ Agent B spawned with 17,832 tokens (89% memory savings)</span>{'\n'}
                  <span className="statline">🚀 Handoff complete in 1.4s — execution resumed.</span>{'\n'}
                  <span className="cursor"></span>
                </>
              )}

              {demoProfile === 'ast' && (
                <span className="ans">{`{
  "delta_id": "snap_948f21a8",
  "target_repo": "payment-middleware",
  "modified_nodes": [
    { "type": "FunctionDef", "name": "process_retry", "status": "COMPLETED", "line": 142 },
    { "type": "AsyncDef", "name": "verify_signature", "status": "IN_PROGRESS", "line": 188 }
  ],
  "token_saving": "89.2%"
}`}</span>
              )}

              {demoProfile === 'whynot' && (
                <span className="you">{`// Why-NOT Dead-End Memory Graph (Task #4892)
(Attempt #1: Synchronous Webhook) ────► FAILED (Timeout 5000ms)
(Attempt #2: Exponential Backoff) ────► REJECTED (Race Condition in lock)
(Attempt #3: Redis Distributed Lock) ──► ACTIVE PATH ✓ (Handed off to Agent B)`}</span>
              )}
            </div>
          </div>
        </section>

        {/* ── 04: BENCHMARKS ────────────────────────────────────────────────── */}
        <section id="ladder-sec" className="reveal-on-scroll">
          <div className="snum">04 — benchmarks</div>
          <h2>Empirical Evaluation</h2>

          <table className="ladder reveal-on-scroll delay-1">
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Completion</th>
                <th></th>
                <th>Continuity Details</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><b>Relay (Checkpoint + Hybrid + Why-NOT)</b></td>
                <td className="spd">87.0%</td>
                <td className="bar-td">
                  <div className="sbar" style={{ width: '87%' }}></div>
                </td>
                <td><b>0.81 score</b> · 4.2% duplicate work · 1.4s handoff</td>
              </tr>
              <tr>
                <td>Naïve Summary Prompting</td>
                <td style={{ color: 'var(--gold)' }}>58.0%</td>
                <td className="bar-td">
                  <div className="sbar" style={{ width: '58%', background: 'var(--gold)' }}></div>
                </td>
                <td>0.45 score · 27.1% duplicate work · 3.8s handoff</td>
              </tr>
              <tr>
                <td>Naive Truncation (FIFO)</td>
                <td style={{ color: '#ef4444' }}>41.0%</td>
                <td className="bar-td">
                  <div className="sbar" style={{ width: '41%', background: '#ef4444' }}></div>
                </td>
                <td>0.23 score · 48.5% duplicate work · Context lost</td>
              </tr>
            </tbody>
          </table>
        </section>

        {/* ── 05: ARCHITECTURE ──────────────────────────────────────────────── */}
        <section id="architecture" className="reveal-on-scroll">
          <div className="snum">05 — architecture</div>
          <h2>Four Decoupled Layers</h2>

          <div className="models-grid">
            <div className="mcard reveal-on-scroll delay-1">
              <span className="status live">live</span>
              <h3>Core Interceptor</h3>
              <p>Wraps execution loop. Triggers handoff at 85% limit.</p>
            </div>

            <div className="mcard reveal-on-scroll delay-2">
              <span className="status live">live</span>
              <h3>Why-NOT Memory</h3>
              <p>Indexes rejected paths &amp; failed hypotheses per-task.</p>
            </div>

            <div className="mcard reveal-on-scroll delay-3">
              <span className="status live">live</span>
              <h3>AST Delta Indexer</h3>
              <p>Extracts exact structural diffs — functions, imports, mutations.</p>
            </div>

            <div className="mcard reveal-on-scroll delay-4">
              <span className="status live">live</span>
              <h3>Hybrid Retrieval</h3>
              <p>BM25 keyword search + FAISS vector graph index.</p>
            </div>
          </div>
        </section>

        {/* ── 06: ROADMAP ───────────────────────────────────────────────────── */}
        <section id="roadmap" className="reveal-on-scroll">
          <div className="snum">06 — roadmap</div>
          <h2>Engineering Roadmap</h2>

          <div className="pillars" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
            <div className="pillar reveal-on-scroll delay-1" style={{ borderColor: 'rgba(94, 232, 143, 0.3)' }}>
              <div className="ic">✓</div>
              <h3 style={{ color: 'var(--green)' }}>v0.4 — Current</h3>
              <p>
                ✓ Budget Interceptor<br />
                ✓ AST Delta Indexer<br />
                ✓ Why-NOT Memory<br />
                ✓ Hybrid Retrieval
              </p>
            </div>

            <div className="pillar reveal-on-scroll delay-2" style={{ borderColor: 'rgba(215, 95, 215, 0.3)' }}>
              <div className="ic">→</div>
              <h3 style={{ color: 'var(--magenta)' }}>v0.5 — In Progress</h3>
              <p>
                • Claude API driver<br />
                • OpenAI Agents SDK adapter<br />
                • Multi-language AST (Go, Rust)<br />
                • Live benchmark harness
              </p>
            </div>

            <div className="pillar reveal-on-scroll delay-3">
              <div className="ic">○</div>
              <h3 style={{ color: 'var(--dim)' }}>v1.0 — Planned</h3>
              <p>
                • S3 / GCS distributed store<br />
                • LangChain &amp; LlamaIndex adapters<br />
                • Real-time trace visualizer<br />
                • Multi-agent swarm graph
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* ── Minimal Footer ──────────────────────────────────────────────────── */}
      <footer>
        <span>⚡ relay — <a href="https://github.com/yourusername/relay/blob/main/LICENSE">Apache 2.0 license</a></span>
        <a href="https://github.com/yourusername/relay">GitHub</a>
        <a href="#architecture">Architecture</a>
        <a href="#ladder-sec">Benchmark</a>
        <span className="sp">seamless context handoff.</span>
      </footer>
    </>
  );
}
