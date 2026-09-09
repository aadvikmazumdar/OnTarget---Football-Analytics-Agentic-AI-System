import Plot from 'react-plotly.js'
import { plotLayout, plotConfig, accent, fmt } from '@/lib/plotlyTheme'

type Point = { date: string; xG: number; xGA: number; opponent: string; result: string; rank_to_date: number | null }

export function FormChart({ rows, leagueAvg }: { rows: Point[]; leagueAvg: number | null }) {
  return (
    <Plot
      data={[
        ...(leagueAvg != null ? [{
          x: [rows[0]?.date, rows[rows.length - 1]?.date],
          y: [leagueAvg, leagueAvg],
          type: 'scatter' as const, mode: 'lines' as const,
          line: { color: '#5A544D', width: 1, dash: 'dot' as const },
          hovertemplate: `league average ${leagueAvg.toFixed(2)}<extra></extra>`,
        }] : []),
        {
          x: rows.map(d => d.date), y: rows.map(d => d.xG),
          type: 'scatter', mode: 'lines+markers',
          line: { color: accent.rust, width: 1.5 },
          marker: { size: 4, color: accent.rust },
          customdata: rows.map(d => [d.opponent, d.result, fmt.rank(d.rank_to_date)]),
          hovertemplate: '%{customdata[0]} (%{customdata[1]})<br>xG %{y:.2f} · rank %{customdata[2]}<extra></extra>',
        },
      ]}
      layout={{ ...plotLayout, height: 320, autosize: true }}
      config={plotConfig}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}