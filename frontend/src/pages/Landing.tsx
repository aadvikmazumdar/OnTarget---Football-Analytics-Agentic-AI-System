import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

const API = 'http://localhost:8000/api'

const SECTIONS = [
  ['questions', 'the questions'],
  ['form', 'form decay'],
  ['state', 'shot quality'],
  ['press', 'press resistance'],
  ['tags', 'match tags'],
  ['compare', 'vs sofascore'],
  ['dash', 'the dashboard'],
] as const

function useInView<T extends HTMLElement>(threshold = 0.2) {
  const ref = useRef<T | null>(null)
  const [seen, setSeen] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect() } },
      { threshold }
    )
    io.observe(el)
    return () => io.disconnect()
  }, [threshold])
  return { ref, seen }
}

function Reveal({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const { ref, seen } = useInView<HTMLDivElement>()
  return (
    <div ref={ref} className="transition-all duration-700"
      style={{ opacity: seen ? 1 : 0, transform: seen ? 'none' : 'translateY(12px)', transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  )
}

function Split({ id, claim, stat, detail, children }: {
  id: string; claim: string; stat: string; detail: string; children: React.ReactNode
}) {
  const { ref, seen } = useInView<HTMLDivElement>()
  return (
    <div id={id} ref={ref} className="border-t border-rule py-14 scroll-mt-20">
      <div className="flex gap-12 items-center">
        <div className="w-[38%] shrink-0 transition-all duration-700"
          style={{ opacity: seen ? 1 : 0, transform: seen ? 'none' : 'translateY(12px)' }}>
          <h2 className="font-serif text-2xl text-ink leading-snug mb-2">{claim}</h2>
          <div className="font-mono text-sm text-rust mb-3">{stat}</div>
          <p className="font-serif text-sm text-muted leading-relaxed">{detail}</p>
        </div>
        <div className="flex-1 min-w-0">{children}</div>
      </div>
    </div>
  )
}

function FormDecay({ rows }: { rows: { cur5: number; avg_next5: number }[] }) {
  if (!rows.length) return null
  const W = 420, H = 230, P = 30
  const x = (v: number) => P + (v / 15) * (W - P * 2)
  const y = (v: number) => H - P - (v / 15) * (H - P * 2)
  const path = rows.map((r, i) => `${i ? 'L' : 'M'}${x(r.cur5)},${y(r.avg_next5)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
      <line x1={P} y1={H - P} x2={W - P} y2={H - P} stroke="#2B2724" />
      <line x1={P} y1={P} x2={P} y2={H - P} stroke="#2B2724" />
      <line x1={x(0)} y1={y(0)} x2={x(15)} y2={y(15)} stroke="#5A544D" strokeDasharray="3 4" />
      <text x={x(7.5)} y={y(9.6)} fontFamily="IBM Plex Mono" fontSize="9" fill="#5A544D">if form persisted</text>
      <path d={path} fill="none" stroke="#C96A4E" strokeWidth="2"
        strokeDasharray="900" strokeDashoffset="900"
        style={{ animation: 'draw 1.6s cubic-bezier(.2,.8,.2,1) 0.2s forwards' }} />
      <text x={x(7.5)} y={y(5.4)} fontFamily="IBM Plex Mono" fontSize="9" fill="#C96A4E">actual</text>
      <text x={W / 2} y={H - 6} textAnchor="middle" fontFamily="IBM Plex Mono" fontSize="9" fill="#5A544D">points from last 5</text>
    </svg>
  )
}

function GameStateBars({ rows }: { rows: { game_state: string; avg_xg: number }[] }) {
  const clean = (rows ?? []).filter(r => r && typeof r.game_state === 'string')
  if (!clean.length) return null
  const max = Math.max(...clean.map(r => r.avg_xg), 0.001)
  return (
    <div>
      {clean.map((r, i) => (
        <div key={r.game_state} className="flex items-center gap-3 mb-2.5">
          <span className="font-mono text-[10px] text-muted w-24 shrink-0">{r.game_state.replace(/_/g, ' ')}</span>
          <div className="h-3 bg-rust"
            style={{ width: `${(r.avg_xg / max) * 74}%`, animation: `grow 0.8s cubic-bezier(.2,.8,.2,1) ${i * 0.12}s both` }} />
          <span className="font-mono text-[10px] text-muted">{r.avg_xg.toFixed(2)}</span>
        </div>
      ))}
    </div>
  )
}

function PressScatterSvg({ rows }: { rows: { avg_ppda_allowed: number; clinical_rate: number }[] }) {
  if (!rows.length) return null
  const W = 420, H = 240, P = 30
  const xs = rows.map(r => r.avg_ppda_allowed), ys = rows.map(r => r.clinical_rate)
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys)
  const px = (v: number) => P + ((v - x0) / (x1 - x0)) * (W - P * 2)
  const py = (v: number) => H - P - ((v - y0) / (y1 - y0)) * (H - P * 2)
  const n = rows.length
  const mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n
  const slope = xs.reduce((s, v, i) => s + (v - mx) * (ys[i] - my), 0) / xs.reduce((s, v) => s + (v - mx) ** 2, 0)
  const at = (v: number) => my + slope * (v - mx)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
      <line x1={P} y1={H - P} x2={W - P} y2={H - P} stroke="#2B2724" />
      <line x1={P} y1={P} x2={P} y2={H - P} stroke="#2B2724" />
      {rows.map((r, i) => (
        <circle key={i} cx={px(r.avg_ppda_allowed)} cy={py(r.clinical_rate)} r="2" fill="#6E88A8" opacity="0"
          style={{ animation: `fade 0.5s ease-out ${0.2 + (i % 40) * 0.008}s forwards` }} />
      ))}
      <line x1={px(x0)} y1={py(at(x0))} x2={px(x1)} y2={py(at(x1))} stroke="#C96A4E" strokeWidth="2"
        strokeDasharray="500" strokeDashoffset="500"
        style={{ animation: 'draw 1.4s cubic-bezier(.2,.8,.2,1) 0.5s forwards' }} />
      <text x={W / 2} y={H - 6} textAnchor="middle" fontFamily="IBM Plex Mono" fontSize="9" fill="#5A544D">ppda allowed</text>
    </svg>
  )
}

const QUESTIONS = [
  'Does Atlético actually win games they shouldn\'t, or does it just feel that way?',
  'Which teams outperform their xG — finishing, or how they create chances?',
  'Does a team going 1–0 up inflate the opponent\'s xGA because they\'re chasing?',
  'Does pressing predict overperformance, or is it just correlated with good teams?',
  'Do trailing teams create worse chances, or just more desperate ones?',
]

const COMPARISON: [string, boolean, boolean][] = [
  ['xG per match', true, true],
  ['Live data', true, false],
  ['Game-state adjusted xG', false, true],
  ['20-tag match classification', false, true],
  ['xGD consistency across seasons', false, true],
  ['Shot quality by phase', false, true],
  ['Natural language queries', false, true],
]

const CAPABILITIES: [string, string][] = [
  ['form', 'Match-by-match xG against the league average.'],
  ['shots', 'Every shot on a pitch map — taken or conceded.'],
  ['tags', 'Click a tag to see the matches behind it.'],
  ['profile', 'Z-score radar, press resistance, consistency.'],
  ['league', 'Leaderboards across eleven metrics.'],
]

export function Landing() {
  const nav = useNavigate()
  const [decay, setDecay] = useState<any[]>([])
  const [states, setStates] = useState<any[]>([])
  const [press, setPress] = useState<any[]>([])
  const [tagCounts, setTagCounts] = useState<any[]>([])
  const [active, setActive] = useState<string>('questions')

  useEffect(() => {
    axios.get(`${API}/landing/form-regression`).then(r => setDecay(r.data)).catch(() => {})
    axios.get(`${API}/landing/game-state`).then(r => setStates(r.data)).catch(() => {})
    axios.get(`${API}/landing/press-scatter`).then(r => setPress(r.data)).catch(() => {})
    axios.get(`${API}/landing/tag-counts`).then(r => setTagCounts(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    const io = new IntersectionObserver(
      entries => {
        const vis = entries.filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (vis[0]) setActive(vis[0].target.id)
      },
      { rootMargin: '-20% 0px -60% 0px' }
    )
    SECTIONS.forEach(([id]) => {
      const el = document.getElementById(id)
      if (el) io.observe(el)
    })
    return () => io.disconnect()
  }, [])

  const maxTag = Math.max(...tagCounts.map(t => t.count), 1)

  return (
    <div className="h-full overflow-y-auto">
      <style>{`
        @keyframes draw { to { stroke-dashoffset: 0; } }
        @keyframes grow { from { width: 0; } }
        @keyframes fade { to { opacity: 0.45; } }
      `}</style>

      <div className="sticky top-0 z-20 bg-bg border-b border-rule">
        <div className="max-w-6xl mx-auto px-8 py-4 flex items-center justify-between">
          <span className="font-serif text-lg text-ink">OnTarget</span>
          <button onClick={() => nav('/dashboard')}
            className="font-mono text-[11px] text-rust border border-rust rounded px-3 py-1.5 hover:bg-rust hover:text-bg transition-colors">
            open dashboard →
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-8 flex gap-10">
        <nav className="w-36 shrink-0 hidden lg:block">
          <div className="sticky top-28 py-24">
            {SECTIONS.map(([id, label]) => (
              <a key={id} href={`#${id}`}
                className={`block font-mono text-[10px] py-1.5 pl-3 border-l transition-colors ${
                  active === id ? 'text-rust border-rust' : 'text-faint border-rule hover:text-muted'
                }`}>
                {label}
              </a>
            ))}
          </div>
        </nav>

        <div className="flex-1 min-w-0">
          <div className="py-24">
            <h1 className="font-serif text-5xl text-ink leading-[1.08] mb-6 max-w-2xl">
              An AI football analyst that happens to have a dashboard.
            </h1>
            <p className="font-serif text-lg text-muted leading-relaxed max-w-xl mb-6">
              SofaScore tells you what happened. OnTarget tells you why it happened, how unusual it was,
              and what's likely to happen next.
            </p>
            <div className="font-mono text-[11px] uppercase tracking-wider text-faint">
              8,982 matches · 224,676 shots · top 5 leagues · 2020–2024
            </div>
          </div>

          <div id="questions" className="border-t border-rule py-14 scroll-mt-20">
            <Reveal>
              <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-8">
                the questions no public platform answers
              </div>
            </Reveal>
            {QUESTIONS.map((q, i) => (
              <Reveal key={q} delay={i * 70}>
                <div className="flex gap-5 py-3.5 border-b border-rule">
                  <span className="font-mono text-xs text-rust shrink-0 pt-1">{String(i + 1).padStart(2, '0')}</span>
                  <span className="font-serif text-base text-ink leading-snug">{q}</span>
                </div>
              </Reveal>
            ))}
          </div>

          <Split id="form"
            claim="Form decays faster than you think."
            stat="15 pts → 5.2"
            detail="A team on 15 points from five matches averages 9.9 in the next five. A team on zero averages 4.7. Real, but a fifteen-point spread collapses to five.">
            <FormDecay rows={decay} />
          </Split>

          <Split id="state"
            claim="Chasing the game ruins shot quality."
            stat="2.38 vs 1.03"
            detail="Teams two goals ahead generate 2.38 xG per match. Teams losing generate 1.03. Desperation produces volume, not chances.">
            <GameStateBars rows={states} />
          </Split>

          <Split id="press"
            claim="Press resistance beats pressing."
            stat="r = 0.394"
            detail="Resisting the opposition press correlates with clinical finishing across 486 team-seasons. Own pressing intensity correlates at r = 0.021 — nothing.">
            <PressScatterSvg rows={press} />
          </Split>

          <div id="tags" className="border-t border-rule py-14 scroll-mt-20">
            <div className="flex gap-12">
              <div className="w-[38%] shrink-0">
                <Reveal>
                  <h2 className="font-serif text-2xl text-ink leading-snug mb-2">Every match gets a story.</h2>
                  <div className="font-mono text-sm text-rust mb-3">20 tags</div>
                  <p className="font-serif text-sm text-muted leading-relaxed">
                    Perfect Heist. Grand Robbery. Smash and Grab. GK Nightmare. Every match classified by
                    what happened against what the xG said should have — the most dramatic reading wins.
                  </p>
                </Reveal>
              </div>
              <div className="flex-1 min-w-0">
                {tagCounts.slice(0, 12).map((t, i) => (
                  <div key={t.tag} className="flex items-center gap-3 mb-1.5">
                    <span className="font-mono text-[10px] text-muted w-28 shrink-0">{t.tag.replace(/_/g, ' ')}</span>
                    <div className="h-2.5 bg-rust"
                      style={{ width: `${(t.count / maxTag) * 68}%`, animation: `grow 0.7s cubic-bezier(.2,.8,.2,1) ${i * 0.05}s both` }} />
                    <span className="font-mono text-[10px] text-faint">{t.count.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div id="compare" className="border-t border-rule py-14 scroll-mt-20">
            <div className="flex gap-12">
              <div className="w-[38%] shrink-0">
                <Reveal>
                  <h2 className="font-serif text-2xl text-ink leading-snug mb-2">What you don't get elsewhere.</h2>
                  <p className="font-serif text-sm text-muted leading-relaxed">
                    Fewer competitions, far more depth. Five leagues, five seasons, every shot enriched with
                    game state, zone, and phase.
                  </p>
                </Reveal>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between py-2 border-b border-rule">
                  <span className="flex-1" />
                  <span className="font-mono text-[10px] text-faint w-20 text-center">sofascore</span>
                  <span className="font-mono text-[10px] text-rust w-20 text-center">ontarget</span>
                </div>
                {COMPARISON.map(([label, sofa, ot], i) => (
                  <Reveal key={label} delay={i * 45}>
                    <div className="flex items-baseline justify-between py-2 border-b border-rule">
                      <span className="text-sm text-ink flex-1">{label}</span>
                      <span className={`font-mono text-xs w-20 text-center ${sofa ? 'text-muted' : 'text-faint'}`}>{sofa ? '✓' : '—'}</span>
                      <span className={`font-mono text-xs w-20 text-center ${ot ? 'text-rust' : 'text-faint'}`}>{ot ? '✓' : '—'}</span>
                    </div>
                  </Reveal>
                ))}
              </div>
            </div>
          </div>

          <div id="dash" className="border-t border-rule py-14 scroll-mt-20">
            <div className="flex gap-12">
              <div className="w-[38%] shrink-0">
                <Reveal>
                  <h2 className="font-serif text-2xl text-ink leading-snug mb-2">Explore it yourself.</h2>
                  <button onClick={() => nav('/dashboard')}
                    className="mt-4 font-mono text-xs text-rust border border-rust rounded px-4 py-2 hover:bg-rust hover:text-bg transition-colors">
                    open the dashboard →
                  </button>
                </Reveal>
              </div>
              <div className="flex-1 min-w-0">
                {CAPABILITIES.map(([name, desc]) => (
                  <div key={name} className="flex items-baseline gap-5 py-2.5 border-b border-rule">
                    <span className="font-mono text-xs text-rust w-14 shrink-0">{name}</span>
                    <span className="text-sm text-muted">{desc}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="h-24" />
        </div>
      </div>
    </div>
  )
}