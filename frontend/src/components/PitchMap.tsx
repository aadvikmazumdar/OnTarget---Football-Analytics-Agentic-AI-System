import Plot from 'react-plotly.js'
import { plotConfig, accent } from '@/lib/plotlyTheme'

type Shot = {
  X: number; Y: number; xG: number
  result: string; situation: string
  player: string; date: string
    other_team?: string
}

const RULE = '#2B2724'
const line = (x0: number, y0: number, x1: number, y1: number) => ({
  type: 'line' as const, x0, y0, x1, y1,
  line: { color: RULE, width: 1 }, layer: 'below' as const,
})

const SHAPES = [
  line(0.5, 0, 0.5, 1), line(1, 0, 1, 1), line(0.5, 0, 1, 0), line(0.5, 1, 1, 1),
  line(0.84, 0.21, 1, 0.21), line(0.84, 0.79, 1, 0.79), line(0.84, 0.21, 0.84, 0.79),
  line(0.945, 0.37, 1, 0.37), line(0.945, 0.63, 1, 0.63), line(0.945, 0.37, 0.945, 0.63),
]

export function PitchMap({ shots, height = 420 }: { shots: Shot[]; height?: number }) {
  const goals = shots.filter(s => s.result === 'Goal')
  const misses = shots.filter(s => s.result !== 'Goal')

  const trace = (rows: Shot[], color: string, size: number, opacity: number) => ({
    x: rows.map(s => s.X), y: rows.map(s => s.Y),
    type: 'scattergl' as const, mode: 'markers' as const,
    marker: { size, color, opacity, line: { width: 0 } },
    customdata: rows.map(s => [s.player, s.other_team ?? '', s.xG.toFixed(2), s.situation]),
    hovertemplate: '%{customdata[0]}<br>%{customdata[1]}<br>xG %{customdata[2]} - %{customdata[3]}<extra></extra>',
  })

  return (
    <Plot
      data={[trace(misses, accent.slate, 5, 0.35), trace(goals, accent.rust, 7, 0.9)]}
      layout={{
        paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
        margin: { l: 0, r: 0, t: 0, b: 0 },
        height, showlegend: false,
        xaxis: { range: [0.5, 1.0], visible: false, fixedrange: true, constrain: 'domain' },
        yaxis: { range: [0, 1], visible: false, fixedrange: true, scaleanchor: 'x', scaleratio: 0.772, constrain: 'domain' },
        hoverlabel: {
          bgcolor: '#1E1C1A', bordercolor: RULE,
          font: { family: 'IBM Plex Mono, monospace', size: 11, color: '#EDE8E1' },
        },
        shapes: SHAPES,
      }}
      config={plotConfig}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}