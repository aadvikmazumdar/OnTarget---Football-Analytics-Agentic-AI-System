export const plotLayout = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  font: { family: 'IBM Plex Mono, monospace', size: 11, color: '#857D74' },
  margin: { l: 48, r: 24, t: 16, b: 40 },
  xaxis: {
    gridcolor: '#2B2724',
    zeroline: false,
    linecolor: '#2B2724',
    tickfont: { family: 'IBM Plex Mono, monospace', size: 10, color: '#857D74' },
  },
  yaxis: {
    gridcolor: '#2B2724',
    zeroline: false,
    linecolor: '#2B2724',
    tickfont: { family: 'IBM Plex Mono, monospace', size: 10, color: '#857D74' },
  },
  showlegend: false,
  hoverlabel: {
    bgcolor: '#1E1C1A',
    bordercolor: '#2B2724',
    font: { family: 'IBM Plex Mono, monospace', size: 11, color: '#EDE8E1' },
  },
} as const

export const plotConfig = { displayModeBar: false, responsive: true } as const

export const accent = { rust: '#C96A4E', olive: '#8FA36E', slate: '#6E88A8' } as const

export const fmt = {
  xg: (n: number) => n.toFixed(2),
  rate: (n: number) => n.toFixed(3),
  rank: (n: number | null) => (n == null ? '—' : String(Math.round(n))),
}