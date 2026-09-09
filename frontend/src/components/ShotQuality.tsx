import Plot from 'react-plotly.js'
import { plotLayout, plotConfig, accent } from '@/lib/plotlyTheme'

type Shot = { xG: number; game_state: string; situation: string; counter_tier: string }

function boxTrace(rows: Shot[], key: 'game_state' | 'situation') {
  const clean = (rows ?? []).filter(r => r && typeof r[key] === 'string' && typeof r.xG === 'number')
  const groups = Array.from(new Set(clean.map(r => r[key])))
  return groups.map(g => {
    const vals = clean.filter(r => r[key] === g).map(r => r.xG)
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length
    return { group: g, mean, n: vals.length }
  }).sort((a, b) => b.mean - a.mean)
}

export function ShotQuality({ rows, groupBy }: { rows: Shot[]; groupBy: 'game_state' | 'situation' }) {
  const stats = boxTrace(rows, groupBy)
  if (!stats.length) return null

  return (
    <Plot
      data={[{
        x: stats.map(s => s.mean),
        y: stats.map(s => s.group.replace(/_/g, ' ')),
        type: 'bar',
        orientation: 'h',
        marker: { color: accent.rust },
        customdata: stats.map(s => [s.n]),
        hovertemplate: '%{y}<br>avg xG %{x:.3f} · %{customdata[0]} shots<extra></extra>',
      }]}
      layout={{
        ...plotLayout,
        height: Math.max(220, stats.length * 26 + 60),
        autosize: true,
        margin: { l: 130, r: 24, t: 8, b: 36 },
        xaxis: { ...plotLayout.xaxis, type: 'linear', title: { text: 'average xG per shot', font: { size: 10, color: '#5A544D' } } },
        yaxis: { ...plotLayout.yaxis, type: 'category', autorange: 'reversed', automargin: true },
      }}
      config={plotConfig}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}