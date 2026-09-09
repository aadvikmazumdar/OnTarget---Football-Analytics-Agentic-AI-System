import Plot from 'react-plotly.js'
import { plotLayout, plotConfig, accent } from '@/lib/plotlyTheme'

type TagData = {
  counts: Record<string, number>
  timeline: { date: string; tags: string[] }[]
}

export function TagCounts({ data, onSelect }: { data: TagData; onSelect?: (tag: string) => void }) {
  const entries = Object.entries(data.counts).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1])

  return (
    <Plot
      data={[{
        x: entries.map(([, v]) => v),
        y: entries.map(([k]) => k.replace(/_/g, ' ')),
        type: 'bar',
        orientation: 'h',
        marker: { color: accent.rust },
        hovertemplate: '%{y}: %{x}<extra></extra>',
      }]}
      layout={{
        ...plotLayout,
        height: Math.max(240, entries.length * 24 + 60),
        autosize: true,
        margin: { l: 130, r: 24, t: 8, b: 32 },
        xaxis: { ...plotLayout.xaxis, type: 'linear' },
        yaxis: { ...plotLayout.yaxis, type: 'category', autorange: 'reversed', automargin: true },
      }}
      config={plotConfig}
      style={{ width: '100%' }}
      useResizeHandler
      onClick={(e: any) => {
        const label = e?.points?.[0]?.y
        if (label && onSelect) onSelect(label.replace(/ /g, '_'))
      }}
    />
  )
}

export function TagTimeline({ data }: { data: TagData }) {
  const allTags = Array.from(new Set(data.timeline.flatMap(d => d.tags)))
  const points = data.timeline.flatMap(d =>
    d.tags.map(t => ({ date: d.date.slice(0, 10), tag: t }))
  )

  return (
    <Plot
      data={[{
        x: points.map(p => p.date),
        y: points.map(p => p.tag.replace(/_/g, ' ')),
        type: 'scatter',
        mode: 'markers',
        marker: { size: 7, color: accent.rust, opacity: 0.8 },
        hovertemplate: '%{x}<br>%{y}<extra></extra>',
      }]}
      layout={{
        ...plotLayout,
        height: Math.max(240, allTags.length * 26 + 70),
        autosize: true,
        margin: { l: 130, r: 24, t: 8, b: 40 },
      }}
      config={plotConfig}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}