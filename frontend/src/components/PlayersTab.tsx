import { useEffect, useState } from 'react'
import axios from 'axios'
import Plot from 'react-plotly.js'
import { plotConfig, accent } from '@/lib/plotlyTheme'

const API = 'http://localhost:8000/api'

const METRICS: [string, string][] = [
  ['shots_per90', 'shots per 90'],
  ['npg_per90', 'non-pen goals per 90'],
  ['npxg_per90', 'non-pen xG per 90'],
  ['np_residual', 'finishing residual'],
  ['avg_shot_xg', 'avg xG per shot'],
  ['np_conversion', 'conversion rate'],
  ['xa_per90', 'xA per 90'],
  ['kp_per90', 'key passes per 90'],
  ['xgchain_per90', 'xGChain per 90'],
]

const POSITIONS: [string, string][] = [
  ['F', 'forwards'],
  ['M', 'midfielders'],
  ['D', 'defenders'],
]

type Row = {
  id: number; player_name: string; main_team: string; main_league: string
  position: string; minutes: number; np_shots: number
  key_passes: number; assists: number; np_goals: number
  position_ambiguous: boolean; value: number; percentile: number
}

// The volume column has to match what's being ranked - a shot count next to an
// xA ranking tells you nothing about whether that xA is trustworthy.
type VolKey = 'np_shots' | 'key_passes'
type OutKey = 'np_goals' | 'assists'

const VOLUME_FOR: Record<string, [VolKey, string]> = {
  shots_per90:    ['np_shots', 'shots'],
  npg_per90:      ['np_shots', 'shots'],
  npxg_per90:     ['np_shots', 'shots'],
  np_residual:    ['np_shots', 'shots'],
  avg_shot_xg:    ['np_shots', 'shots'],
  np_conversion:  ['np_shots', 'shots'],
  xa_per90:       ['key_passes', 'key passes'],
  kp_per90:       ['key_passes', 'key passes'],
  xgchain_per90:  ['key_passes', 'key passes'],
}

// Volume is the attempt count, outcome is what came of it. Both have to match
// the metric family - assists next to a shot-volume ranking says nothing.
const OUTCOME_FOR: Record<string, [OutKey, string]> = {
  shots_per90:    ['np_goals', 'np goals'],
  npg_per90:      ['np_goals', 'np goals'],
  npxg_per90:     ['np_goals', 'np goals'],
  np_residual:    ['np_goals', 'np goals'],
  avg_shot_xg:    ['np_goals', 'np goals'],
  np_conversion:  ['np_goals', 'np goals'],
  xa_per90:       ['assists', 'assists'],
  kp_per90:       ['assists', 'assists'],
  xgchain_per90:  ['assists', 'assists'],
}

const fmt = (v: number | null, dp = 2) =>
  v === null || v === undefined || Number.isNaN(v) ? '—' : v.toFixed(dp)

export function PlayersTab({ league, team }: { league?: string; team?: string }) {
  const [position, setPosition] = useState('F')
  const [metric, setMetric] = useState('shots_per90')
  const [minMinutes, setMinMinutes] = useState(2700)
  const [scope, setScope] = useState<'all' | 'team'>('all')
  const [order, setOrder] = useState('desc')
  const [limit, setLimit] = useState(25)
  const [rows, setRows] = useState<Row[]>([])
  const [meta, setMeta] = useState<any>(null)
  const [dist, setDist] = useState<number[]>([])
  const [selected, setSelected] = useState<any | null>(null)

  useEffect(() => {
    const p = new URLSearchParams({
      metric, position, order, limit: String(limit),
      min_minutes: String(minMinutes),
    })
    if (league) p.set('league', league)
    if (team && scope === 'team') p.set('team', team)
    axios.get(`${API}/players/leaderboard?${p}`)
      .then(r => { setRows(r.data.rows); setMeta(r.data) })
      .catch(() => { setRows([]); setMeta(null) })
  }, [metric, position, league, team, scope, minMinutes, order, limit])

  useEffect(() => {
    const p = new URLSearchParams({
      metric, position, min_minutes: String(minMinutes),
    })
    axios.get(`${API}/players/distribution?${p}`)
      .then(r => setDist(r.data.values)).catch(() => setDist([]))
  }, [metric, position, minMinutes])

  useEffect(() => { setSelected(null) }, [position, metric, scope])
  useEffect(() => { if (!team) setScope('all') }, [team])

  const pick = (id: number) => {
    if (selected?.player?.id === id) { setSelected(null); return }
    axios.get(`${API}/players/${id}`)
      .then(r => setSelected(r.data)).catch(() => setSelected(null))
  }

  const marker = selected?.player?.[metric] ?? null
  const [volKey, volLabel] = VOLUME_FOR[metric] ?? ['np_shots', 'shots']
  const [outKey, outLabel] = OUTCOME_FOR[metric] ?? ['np_goals', 'np goals']

  return (
    <>
      <div className="flex items-baseline justify-between mb-3 gap-3 flex-wrap">
        <div className="font-mono text-[11px] uppercase tracking-wider text-faint">
          {meta?.label ?? metric} · {order === 'desc' ? 'highest' : 'lowest'} {rows.length} of {dist.length} {position}
        </div>
        <div className="flex gap-2">
          <select value={position} onChange={e => setPosition(e.target.value)}
            className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-[11px] text-muted focus:outline-none focus:border-muted">
            {POSITIONS.map(([v, l]) => (
              <option key={v} value={v} className="bg-panel">{l}</option>
            ))}
          </select>
          <select value={metric} onChange={e => setMetric(e.target.value)}
            className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-[11px] text-muted focus:outline-none focus:border-muted">
            {METRICS.map(([v, l]) => (
              <option key={v} value={v} className="bg-panel">{l}</option>
            ))}
          </select>
          <select value={minMinutes} onChange={e => setMinMinutes(Number(e.target.value))}
            className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-[11px] text-muted focus:outline-none focus:border-muted">
            {[900, 2700, 4500, 6000].map(v => (
              <option key={v} value={v} className="bg-panel">{v}+ mins</option>
            ))}
          </select>
          {team && (
            <select value={scope} onChange={e => setScope(e.target.value as 'all' | 'team')}
              className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-[11px] text-muted focus:outline-none focus:border-muted">
              <option value="all" className="bg-panel">all teams</option>
              <option value="team" className="bg-panel">{team} only</option>
            </select>
          )}
          <select value={order} onChange={e => setOrder(e.target.value)}
            className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-[11px] text-muted focus:outline-none focus:border-muted">
            <option value="desc" className="bg-panel">highest first</option>
            <option value="asc" className="bg-panel">lowest first</option>
          </select>
          <select value={limit} onChange={e => setLimit(Number(e.target.value))}
            className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-[11px] text-muted focus:outline-none focus:border-muted">
            {[10, 25, 50, 100].map(v => (
              <option key={v} value={v} className="bg-panel">top {v}</option>
            ))}
          </select>
        </div>
      </div>

      <p className="font-serif text-sm text-muted leading-relaxed mb-4 max-w-prose">
        Percentiles are against the same position, not all players — 1.0 shots per 90 is
        high for a defender and low for a forward. Penalties and own goals are excluded
        from every finishing figure.
      </p>

      {dist.length > 0 && (
        <div className="mb-5">
          <Plot
            data={[
              {
                type: 'histogram', x: dist, nbinsx: 45,
                marker: { color: '#6E88A8' },
                hovertemplate: '%{x:.2f} · %{y} players<extra></extra>',
              },
              ...(marker !== null ? [{
                type: 'scatter' as const, mode: 'lines' as const,
                x: [marker, marker], y: [0, Math.max(1, dist.length / 6)],
                line: { color: accent.rust, width: 2 },
                hovertemplate: `${selected?.player?.player_name}: %{x:.2f}<extra></extra>`,
              }] : []),
            ]}
            layout={{
              paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
              height: 200, margin: { l: 40, r: 20, t: 10, b: 34 },
              showlegend: false, bargap: 0.02,
              font: { family: 'IBM Plex Mono, monospace', size: 10, color: '#857D74' },
              xaxis: { gridcolor: '#2B2724', zeroline: false, linecolor: '#2B2724' },
              yaxis: { gridcolor: '#2B2724', zeroline: false, linecolor: '#2B2724' },
              hoverlabel: {
                bgcolor: '#1E1C1A', bordercolor: '#2B2724',
                font: { family: 'IBM Plex Mono, monospace', size: 11, color: '#EDE8E1' },
              },
            }}
            config={plotConfig}
            style={{ width: '100%' }}
            useResizeHandler
          />
        </div>
      )}

      <div className="overflow-hidden">
        <table className="w-full font-mono text-[11px]">
          <thead>
            <tr className="text-faint uppercase tracking-wider border-b border-rule">
              <th className="text-left py-1.5 font-normal w-8">#</th>
              <th className="text-left py-1.5 font-normal">player</th>
              <th className="text-left py-1.5 font-normal">team</th>
              <th className="text-right py-1.5 font-normal">mins</th>
              <th className="text-right py-1.5 font-normal">{volLabel}</th>
              <th className="text-right py-1.5 font-normal">{outLabel}</th>
              <th className="text-right py-1.5 font-normal">value</th>
              <th className="text-right py-1.5 font-normal">pct</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const on = selected?.player?.id === r.id
              const isTeam = team && r.main_team === team
              return (
                <tr key={r.id} onClick={() => pick(r.id)}
                  className={`border-b border-rule/40 cursor-pointer ${
                    on ? 'text-rust' : isTeam ? 'text-ink' : 'text-muted'} hover:text-ink`}>
                  <td className="py-1.5 text-faint">{i + 1}</td>
                  <td className="py-1.5">
                    {r.player_name}
                    {r.position_ambiguous && (
                      <span className="text-faint" title="moves between roles across seasons"> *</span>
                    )}
                  </td>
                  <td className="py-1.5 text-faint">{r.main_team}</td>
                  <td className="py-1.5 text-right text-faint">{r.minutes}</td>
                  <td className="py-1.5 text-right text-faint">{r[volKey]}</td>
                  <td className="py-1.5 text-right text-faint">{r[outKey]}</td>
                  <td className="py-1.5 text-right">{fmt(r.value, 3)}</td>
                  <td className="py-1.5 text-right text-faint">{fmt(r.percentile, 0)}</td>
                </tr>
              )
            }).flatMap((el, i) => {
              const r = rows[i]
              if (selected?.player?.id !== r.id) return [el]
              return [el, (
                <tr key={r.id + '-detail'}>
                  <td colSpan={8} className="p-0">
                    <PlayerDetail data={selected} />
                  </td>
                </tr>
              )]
            })}
          </tbody>
        </table>
        {rows.some(r => r.position_ambiguous) && (
          <p className="font-mono text-[10px] text-faint mt-2">
            * position is minutes-weighted; these players moved between roles across seasons
          </p>
        )}
      </div>

    </>
  )
}

function PlayerDetail({ data }: { data: any }) {
  const p = data.player
  const c = data.cohort
  const foot = [
    ['left', p.shots_leftfoot, p.residual_leftfoot],
    ['right', p.shots_rightfoot, p.residual_rightfoot],
    ['head', p.shots_head, p.residual_head],
  ] as [string, number, number][]

  // Percentile axes, not sigma. Percentiles are bounded 0-100 and read directly
  // as "top 10% of forwards"; a +4 sigma outlier would blow the scale.
  const AXES: [string, string][] = [
    ['shots_per90_pct', 'shot volume'],
    ['npxg_per90_pct', 'chance quality'],
    ['np_residual_per90_pct', 'finishing'],
    ['xa_per90_pct', 'creation'],
    ['kp_per90_pct', 'key passes'],
    ['xgchain_per90_pct', 'involvement'],
  ]
  const vals = AXES.map(([k]) => p[k] ?? 0)

  return (
    <div className="mt-6 pt-5 border-t border-rule">
      <div className="flex items-baseline gap-3 mb-1">
        <span className="font-serif text-xl text-ink">{p.player_name}</span>
        <span className="font-mono text-[11px] text-faint">
          {p.main_team} · {p.position}
          {p.position_ambiguous ? ' (ambiguous)' : ''} · {p.minutes} mins · {p.seasons} seasons
        </span>
      </div>

      <p className="font-serif text-base text-muted leading-relaxed max-w-prose mb-5">
        {p.finishing_verdict?.replace(/_/g, ' ')} · {p.volume_verdict?.replace(/_/g, ' ')} ·{' '}
        {p.creation_verdict?.replace(/_/g, ' ')} · trend {p.trend_verdict}
      </p>

      <div className="grid grid-cols-[340px_1fr] gap-x-10 items-start mb-6">
        <Plot
          data={[{
            type: 'scatterpolar',
            r: [...vals, vals[0]],
            theta: [...AXES.map(([, l]) => l), AXES[0][1]],
            fill: 'toself',
            fillcolor: 'rgba(201,106,78,0.15)',
            line: { color: accent.rust, width: 1.6 },
            hovertemplate: '%{theta}: %{r:.0f}th percentile<extra></extra>',
          }]}
          layout={{
            paper_bgcolor: 'transparent',
            height: 300,
            margin: { l: 55, r: 55, t: 24, b: 24 },
            showlegend: false,
            font: { family: 'IBM Plex Mono, monospace', size: 10, color: '#857D74' },
            polar: {
              bgcolor: 'transparent',
              radialaxis: {
                range: [0, 100], gridcolor: '#2B2724', linecolor: '#2B2724',
                tickvals: [25, 50, 75, 100],
                tickfont: { size: 9, color: '#5A544D' },
              },
              angularaxis: { gridcolor: '#2B2724', linecolor: '#2B2724' },
            },
            hoverlabel: {
              bgcolor: '#1E1C1A', bordercolor: '#2B2724',
              font: { family: 'IBM Plex Mono, monospace', size: 11, color: '#EDE8E1' },
            },
          }}
          config={plotConfig}
          style={{ width: '100%' }}
          useResizeHandler
        />
        <div className="pt-2">
          <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-2">
            percentile vs {p.position} · {c.n} players
          </div>
          <p className="font-serif text-sm text-muted leading-relaxed max-w-prose">
            Every axis is ranked against the same position across all five leagues,
            so 90 means top 10% of {p.position === 'F' ? 'forwards'
              : p.position === 'M' ? 'midfielders' : 'defenders'} — not top 10% of all players.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-10 gap-y-5">
        <Block title="finishing">
          <Stat k="non-pen goals" v={p.np_goals} />
          <Stat k="non-pen xG" v={fmt(p.np_xg)} />
          <Stat k="residual" v={fmt(p.np_residual)} accent />
          <Stat k="residual per 90 vs position" v={<Sigma z={p.np_residual_per90_z} />} />
          <Stat k="conversion vs position" v={<Sigma z={p.np_conversion_z} />} />
          <Stat k="conversion" v={`${fmt(p.np_conversion * 100, 1)}%`} />
          <Stat k="avg xG / shot" v={fmt(p.avg_shot_xg, 3)} />
          <Stat k="shot quality vs position" v={<Sigma z={p.avg_shot_xg_z} />} />
          {p.pens_taken > 0 && (
            <Stat k="penalties" v={`${p.pens_scored}/${p.pens_taken} (excluded above)`} />
          )}
        </Block>

        <Block title="shot volume">
          <Stat k="per 90" v={fmt(p.shots_per90, 2)} accent />
          <Stat k="percentile" v={`${fmt(p.shots_per90_pct, 0)}th among ${p.position}`} />
          <Stat k="sigma" v={<Sigma z={p.shots_per90_z} />} />
          <Stat k="npG per 90" v={`${fmt(p.npg_per90, 3)} (${fmt(p.npg_per90_pct, 0)}th)`} />
          <Stat k="npxG per 90 sigma" v={<Sigma z={p.npxg_per90_z} />} />
          <Stat k={`${p.position} p10 / p50 / p90`}
            v={`${fmt(c.shots_p10, 2)} / ${fmt(c.shots_p50, 2)} / ${fmt(c.shots_p90, 2)}`} />
          <Stat k="cohort size" v={c.n} />
        </Block>

        <Block title="foot">
          {foot.map(([name, shots, res]) => (
            <Stat key={name} k={name}
              v={shots ? `${shots} shots · ${fmt(res, 1)} vs xG` : '—'} />
          ))}
          <Stat k="verdict" v={p.foot_verdict ?? '—'} />
        </Block>

        <Block title="creation">
          <Stat k="xA" v={fmt(p.xA)} />
          <Stat k="xA per 90" v={`${fmt(p.xa_per90, 3)} (${fmt(p.xa_per90_pct, 0)}th)`} />
          <Stat k="xA sigma" v={<Sigma z={p.xa_per90_z} />} />
          <Stat k="assists" v={p.assists} />
          <Stat k="key passes" v={p.key_passes} />
          <Stat k="key passes per 90" v={<Sigma z={p.kp_per90_z} />} />
          <Stat k="xGChain per 90"
            v={`${fmt(p.xgchain_per90, 3)} (${fmt(p.xgchain_per90_pct, 0)}th)`} />
          <Stat k="xGChain sigma" v={<Sigma z={p.xgchain_per90_z} />} />
          <Stat k="xGBuildup sigma" v={<Sigma z={p.xgbuildup_per90_z} />} />
        </Block>
      </div>

      {p.season_progression && (
        <div className="mt-6">
          <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-1.5">
            season progression · goals minus xG
          </div>
          <div className="font-mono text-xs text-muted">{p.season_progression}</div>
          {p.peak_year && (
            <div className="font-mono text-[11px] text-faint mt-1">
              peak {p.peak_year} ({fmt(p.peak_residual, 1)}) · trough {p.trough_year} ({fmt(p.trough_residual, 1)})
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-2">
        {title}
      </div>
      <div className="space-y-1">{children}</div>
    </div>
  )
}

// Sigma against the same position. Formatted with an explicit sign because the
// direction is the whole point - -1.4 and +1.4 are opposite findings.
function Sigma({ z }: { z: number | null | undefined }) {
  if (z === null || z === undefined || Number.isNaN(z)) return <span className="text-faint">—</span>
  const strong = Math.abs(z) >= 1
  return (
    <span className={strong ? 'text-rust' : 'text-faint'}>
      {z >= 0 ? '+' : ''}{z.toFixed(2)}σ
    </span>
  )
}

function Stat({ k, v, accent }: { k: string; v: any; accent?: boolean }) {
  return (
    <div className="flex justify-between gap-4 font-mono text-[11px]">
      <span className="text-faint">{k}</span>
      <span className={accent ? 'text-rust' : 'text-muted'}>{v}</span>
    </div>
  )
}
