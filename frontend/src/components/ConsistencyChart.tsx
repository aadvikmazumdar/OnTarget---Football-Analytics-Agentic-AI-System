import Plot from 'react-plotly.js'
import { plotLayout, plotConfig, accent } from '@/lib/plotlyTheme'

type Row = {
  team_name: string; league: string; seasons_played: number
  avg_xGD_attack: number; best_xGD_attack_season: number; worst_xGD_attack_season: number
  attack_verdict: string
}

export function ConsistencyChart({ rows, highlight }: { rows: Row[]; highlight?: string }) {
  const ranges = rows.flatMap(r => [
    { x: [r.worst_xGD_attack_season, r.best_xGD_attack_season], y: [r.team_name, r.team_name] },
  ])

  return (
    <Plot
      data={[
        ...ranges.map(g => ({
          x: g.x, y: g.y,
          type: 'scatter' as const, mode: 'lines' as const,
          line: { color: '#2B2724', width: 1 },
          hoverinfo: 'skip' as const,
          showlegend: false,
        })),
        {
          x: rows.map(r => r.avg_xGD_attack),
          y: rows.map(r => r.team_name),
          type: 'scatter', mode: 'markers',
          marker: {
            size: 7,
            color: rows.map(r => (r.team_name === highlight ? accent.rust : accent.slate)),
          },
          customdata: rows.map(r => [r.attack_verdict, r.seasons_played]),
          hovertemplate: '%{y}<br>avg %{x:.2f} · %{customdata[0]} · %{customdata[1]} seasons<extra></extra>',
        },
      ]}
      layout={{
        ...plotLayout,
        height: Math.max(300, rows.length * 22 + 60),
        autosize: true,
        margin: { l: 150, r: 24, t: 8, b: 40 },
        xaxis: { ...plotLayout.xaxis, type: 'linear' },
        yaxis: { ...plotLayout.yaxis, type: 'category', automargin: true },
      }}
      config={plotConfig}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}