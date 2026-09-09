import Plot from 'react-plotly.js'
import { plotConfig, accent } from '@/lib/plotlyTheme'

type Profile = {
  team_name: string; year: number
  xGD_attack_zscore: number; xGD_defence_zscore: number
  clinical_rate_zscore: number; heist_rate_zscore: number; robbery_rate_zscore: number
}

const AXES = [
  ['xGD_attack_zscore', 'finishing (att)'],
  ['xGD_defence_zscore', 'conceding luck'],
  ['clinical_rate_zscore', 'clinical rate'],
  ['heist_rate_zscore', 'heists'],
  ['robbery_rate_zscore', 'robberies'],
] as const

// Oldest to newest, fading up. Newest season takes the rust accent.
const FADE = ['rgba(133,125,116,0.22)', 'rgba(133,125,116,0.34)',
              'rgba(133,125,116,0.48)', 'rgba(133,125,116,0.66)']

export function RadarChart({ rows, season }: { rows: Profile[]; season?: number | null }) {
  if (!rows.length) return null

  const sorted = [...rows].sort((a, b) => a.year - b.year)
  const visible = season != null ? sorted.filter(r => r.year === season) : sorted
  if (!visible.length) return null

  const single = visible.length === 1

  const traces = visible.map((r, i) => {
    const values = AXES.map(([k]) => r[k] ?? 0)
    const isNewest = i === visible.length - 1
    return {
      type: 'scatterpolar' as const,
      name: String(r.year),
      r: [...values, values[0]],
      theta: [...AXES.map(([, label]) => label), AXES[0][1]],
      fill: isNewest ? ('toself' as const) : ('none' as const),
      fillcolor: 'rgba(201,106,78,0.15)',
      line: {
        color: isNewest ? accent.rust : FADE[Math.min(i, FADE.length - 1)],
        width: isNewest ? 1.8 : 1,
      },
      hovertemplate: `${r.year} · %{theta}: %{r:.2f}<extra></extra>`,
    }
  })

  return (
    <Plot
      data={traces}
      layout={{
        paper_bgcolor: 'transparent',
        height: 340,
        margin: { l: 60, r: 60, t: 30, b: single ? 30 : 50 },
        showlegend: !single,
        legend: {
          orientation: 'h', x: 0, y: -0.12,
          font: { family: 'IBM Plex Mono, monospace', size: 10, color: '#857D74' },
        },
        font: { family: 'IBM Plex Mono, monospace', size: 10, color: '#857D74' },
        polar: {
          bgcolor: 'transparent',
          radialaxis: {
            range: [-2.5, 2.5], gridcolor: '#2B2724', linecolor: '#2B2724',
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
  )
}
