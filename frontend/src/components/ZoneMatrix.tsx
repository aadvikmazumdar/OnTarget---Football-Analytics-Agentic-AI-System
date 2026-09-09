import Plot from 'react-plotly.js'
import { plotConfig } from '@/lib/plotlyTheme'

type Cell = { shot_zone: string; situation: string; shots: number; avg_xg: number; goals: number }

export function ZoneMatrix({ rows }: { rows: Cell[] }) {
  const zones = Array.from(new Set(rows.map(r => r.shot_zone)))
  const sits = Array.from(new Set(rows.map(r => r.situation)))

  const z = zones.map(zn => sits.map(s => {
    const c = rows.find(r => r.shot_zone === zn && r.situation === s)
    return c ? c.shots : null
  }))

  const text = zones.map(zn => sits.map(s => {
    const c = rows.find(r => r.shot_zone === zn && r.situation === s)
    return c ? `${c.shots} shots · ${c.goals} goals · avg xG ${c.avg_xg.toFixed(3)}` : ''
  }))

  return (
    <Plot
      data={[{
        z, x: sits, y: zones.map(zn => zn.replace(/_/g, ' ')),
        type: 'heatmap',
        colorscale: [[0, '#1E1C1A'], [1, '#C96A4E']],
        showscale: false,
        text, hovertemplate: '%{y} · %{x}<br>%{text}<extra></extra>',
        xgap: 2, ygap: 2,
      }]}
      layout={{
        paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
        height: Math.max(240, zones.length * 42 + 80),
        autosize: true,
        margin: { l: 120, r: 24, t: 8, b: 70 },
        font: { family: 'IBM Plex Mono, monospace', size: 10, color: '#857D74' },
        xaxis: { type: 'category', tickangle: -35, tickfont: { size: 10, color: '#857D74' } },
        yaxis: { type: 'category', automargin: true, tickfont: { size: 10, color: '#857D74' } },
        hoverlabel: {
          bgcolor: '#1E1C1A', bordercolor: '#2B2724',
          font: { family: 'IBM Plex Mono, monospace', size: 11, color: '#EDE8E1' },
        },
      }}
      config={plotConfig}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}