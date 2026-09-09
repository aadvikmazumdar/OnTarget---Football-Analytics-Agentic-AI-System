import Plot from 'react-plotly.js'
import { plotLayout, plotConfig, accent } from '@/lib/plotlyTheme'

type Row = { team_name: string; league: string; year: number; value: number }

export function Leaderboard({ rows, highlight }: { rows: Row[]; highlight?: string }) {
  const labels = rows.map(r => (r.year ? `${r.team_name} ${r.year}` : r.team_name))

  return (
    <Plot
      data={[{
        x: rows.map(r => r.value),
        y: labels,
        type: 'bar',
        orientation: 'h',
        marker: {
          color: rows.map(r => (r.team_name === highlight ? accent.rust : accent.slate)),
          opacity: rows.map(r => (r.team_name === highlight ? 1 : 0.45)),
        },
        hovertemplate: '%{y}<br>%{x:.3f}<extra></extra>',
      }]}
      layout={{
        ...plotLayout,
        height: Math.max(300, rows.length * 20 + 60),
        autosize: true,
        margin: { l: 170, r: 24, t: 8, b: 36 },
        xaxis: { ...plotLayout.xaxis, type: 'linear' },
        yaxis: { ...plotLayout.yaxis, type: 'category', autorange: 'reversed', automargin: true },
      }}
      config={plotConfig}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}