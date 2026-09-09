import Plot from 'react-plotly.js'
import { plotLayout, plotConfig, accent } from '@/lib/plotlyTheme'

type Row = {
  team_name: string; league: string; year: number
  avg_ppda_allowed: number; clinical_rate: number
}

export function PressScatter({ rows, highlight }: { rows: Row[]; highlight?: string }) {
  const others = rows.filter(r => r.team_name !== highlight)
  const mine = rows.filter(r => r.team_name === highlight)

  const trace = (d: Row[], color: string, size: number, opacity: number) => ({
    x: d.map(r => r.avg_ppda_allowed), y: d.map(r => r.clinical_rate),
    type: 'scatter' as const, mode: 'markers' as const,
    marker: { size, color, opacity, line: { width: 0 } },
    customdata: d.map(r => [r.team_name, r.year, r.clinical_rate.toFixed(3)]),
    hovertemplate: '%{customdata[0]} %{customdata[1]}<br>ppda allowed %{x:.1f} · clinical %{customdata[2]}<extra></extra>',
  })

  return (
    <Plot
      data={[trace(others, accent.slate, 5, 0.3), trace(mine, accent.rust, 8, 1)]}
      layout={{
        ...plotLayout, height: 340, autosize: true,
        xaxis: { ...plotLayout.xaxis, type: 'linear', title: { text: 'ppda allowed', font: { size: 10, color: '#5A544D' } } },
        yaxis: { ...plotLayout.yaxis, type: 'linear', title: { text: 'goals / xG', font: { size: 10, color: '#5A544D' } } },
      }}
      config={plotConfig}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}