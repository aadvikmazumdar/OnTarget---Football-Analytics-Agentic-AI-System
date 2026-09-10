import { useEffect, useState } from 'react'
import axios from 'axios'
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable'
import { PitchMap } from '@/components/PitchMap'
import { PressScatter } from '@/components/PressScatter'
import { FormChart } from '@/components/FormChart'
import { TagCounts } from '@/components/TagChart'
import { RadarChart } from '@/components/RadarChart'
import { PlayersTab } from '@/components/PlayersTab'
import { ConsistencyChart } from '@/components/ConsistencyChart'
import { ShotQuality } from '@/components/ShotQuality'
import { ZoneMatrix } from '@/components/ZoneMatrix'
import { Leaderboard } from '@/components/Leaderboard'

const API = 'http://localhost:8000/api'
const TABS = ['form', 'shots', 'tags', 'profile', 'players', 'league'] as const
const METRICS = [
  'xGD_attack', 'xGD_defence', 'clinical_rate', 'heist_rate',
  'robbery_rate', 'wasteful_rate', 'xG_per_game', 'xGA_per_game',
  'goals_per_game', 'conceded_per_game', 'xGD_per_game',
] as const
type Tab = typeof TABS[number]

type Point = { date: string; year: number; xG: number; xGA: number; opponent: string; result: string; rank_to_date: number | null }

export function Dashboard() {
  const [leagues, setLeagues] = useState<string[]>([])
  const [league, setLeague] = useState('')
  const [teams, setTeams] = useState<string[]>([])
  const [team, setTeam] = useState('')
  const [tab, setTab] = useState<Tab>('form')
  const [loading, setLoading] = useState(false)
  const [tags, setTags] = useState<any>(null)
  const [profile, setProfile] = useState<any[]>([])
  const [consistency, setConsistency] = useState<any[]>([])
  const [selectedTag, setSelectedTag] = useState<string | null>(null)
  const [tagMatches, setTagMatches] = useState<any[]>([])
  const [selectedMatch, setSelectedMatch] = useState<any | null>(null)
  const [matchShots, setMatchShots] = useState<any[]>([])
  const [oppShots, setOppShots] = useState<any[]>([])
  const [quality, setQuality] = useState<any[]>([])
  const [zones, setZones] = useState<any[]>([])
  const [board, setBoard] = useState<any[]>([])
  const [boardMeta, setBoardMeta] = useState<any>(null)
  const [metric, setMetric] = useState<string>('xGD_attack')
  const [boardOrder, setBoardOrder] = useState('')
  const [boardLimit, setBoardLimit] = useState(25)

  const [seasons, setSeasons] = useState<number[]>([])
  const [season, setSeason] = useState<number | null>(null)

  const [form, setForm] = useState<Point[]>([])
  const [leagueAvg, setLeagueAvg] = useState<number | null>(null)
  const [press, setPress] = useState<any[]>([])

  const [shots, setShots] = useState<any[]>([])
  const [opponents, setOpponents] = useState<string[]>([])
  const [opponent, setOpponent] = useState('')
  const [side, setSide] = useState<'taken' | 'conceded'>('taken')
  const Empty = () => <div className="h-[300px] border-t border-rule opacity-30" />

  useEffect(() => {
    axios.get<string[]>(`${API}/leagues`).then(r => setLeagues(r.data))
    axios.get<number[]>(`${API}/seasons`).then(r => setSeasons(r.data))
  }, [])

  useEffect(() => {
    const params = [
      league ? `league=${encodeURIComponent(league)}` : '',
      season != null ? `year=${season}` : '',
    ].filter(Boolean).join('&')
    axios.get(`${API}/press-resistance${params ? `?${params}` : ''}`)
      .then(r => setPress(r.data))
      .catch(() => setPress([]))
  }, [league, season])

  useEffect(() => {
    const params = [
      league ? `league=${encodeURIComponent(league)}` : '',
      season != null ? `year=${season}` : '',
    ].filter(Boolean).join('&')
    axios.get<string[]>(`${API}/teams-by-league${params ? `?${params}` : ''}`).then(r => {
      setTeams(r.data)
      if (!r.data.includes(team)) setTeam(r.data[0] ?? '')
    })
  }, [league, season])

  useEffect(() => {
    if (!team) return
    const controller = new AbortController()
    const q = season != null ? `?year=${season}` : ''
    axios.get<Point[]>(`${API}/teams/${encodeURIComponent(team)}/form${q}`, { signal: controller.signal })
      .then(r => setForm(r.data))
      .catch(() => {})
    return () => controller.abort()
  }, [team, season])

  useEffect(() => {
    if (!team) { setLeagueAvg(null); return }
    const leagueUrl = season != null
      ? `${API}/teams/${encodeURIComponent(team)}/league?year=${season}`
      : `${API}/teams/${encodeURIComponent(team)}/league-any`
    axios.get<string>(leagueUrl)
      .then(r => {
        const avgUrl = season != null
          ? `${API}/league-average-xg?league=${r.data}&year=${season}`
          : `${API}/league-average-xg-all?league=${r.data}`
        return axios.get(avgUrl)
      })
      .then(r => setLeagueAvg(r.data.avg_xg))
      .catch(() => setLeagueAvg(null))
  }, [team, season])

  useEffect(() => {
    if (!team) return
    setOpponent('')
    const q = season != null ? `year=${season}&` : ''
    axios.get<string[]>(`${API}/teams/${encodeURIComponent(team)}/opponents?${q}side=${side}`)
      .then(r => setOpponents(r.data))
  }, [team, season, side])

  useEffect(() => {
    if (!team) return
    const controller = new AbortController()
    setLoading(true)
    const path = side === 'taken' ? 'shots' : 'shots-conceded'
    const params = [
      season != null ? `year=${season}` : '',
      opponent ? `opponent=${encodeURIComponent(opponent)}` : '',
    ].filter(Boolean).join('&')
    axios.get(`${API}/teams/${encodeURIComponent(team)}/${path}${params ? `?${params}` : ''}`, { signal: controller.signal })
      .then(r => setShots(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [team, season, opponent, side])

  useEffect(() => {
    if (!team) return
    setSelectedTag(null)
    const q = season != null ? `?year=${season}` : ''
    axios.get(`${API}/teams/${encodeURIComponent(team)}/tags${q}`)
      .then(r => setTags(r.data))
      .catch(() => setTags(null))
  }, [team, season])

  useEffect(() => {
    if (!team) return
    // Always fetch every season - the radar overlays them and highlights
    // the selected one. Filtering here would collapse it to a single trace.
    axios.get(`${API}/teams/${encodeURIComponent(team)}/profile`)
      .then(r => setProfile(r.data))
      .catch(() => setProfile([]))
  }, [team])

  useEffect(() => {
    const q = league ? `?league=${encodeURIComponent(league)}` : ''
    axios.get(`${API}/consistency${q}`)
      .then(r => setConsistency(r.data))
      .catch(() => setConsistency([]))
  }, [league])

  useEffect(() => {
    if (!team || !selectedTag) { setTagMatches([]); return }
    const q = season != null ? `&year=${season}` : ''
    axios.get(`${API}/teams/${encodeURIComponent(team)}/matches-by-tag?tag=${selectedTag}${q}`)
      .then(r => setTagMatches(r.data))
      .catch(() => setTagMatches([]))
    setSelectedMatch(null)
  }, [team, season, selectedTag])

    useEffect(() => {
    if (!selectedMatch) { setMatchShots([]); setOppShots([]); return }
    const controller = new AbortController()
    const opp = selectedMatch.home_team === team ? selectedMatch.away_team : selectedMatch.home_team
    const id = selectedMatch.match_id

    Promise.all([
      axios.get(`${API}/matches/${id}/shots?team_name=${encodeURIComponent(team)}`, { signal: controller.signal }),
      axios.get(`${API}/matches/${id}/shots?team_name=${encodeURIComponent(opp)}`, { signal: controller.signal }),
    ])
      .then(([mine, theirs]) => {
        setMatchShots(mine.data)
        setOppShots(theirs.data)
      })
      .catch(() => {})

    return () => controller.abort()
  }, [selectedMatch, team])

  useEffect(() => {
    if (!team) return
    const q = season != null ? `?year=${season}` : ''
    axios.get(`${API}/teams/${encodeURIComponent(team)}/shot-quality${q}`)
      .then(r => setQuality(r.data)).catch(() => setQuality([]))
    axios.get(`${API}/teams/${encodeURIComponent(team)}/zone-matrix${q}`)
      .then(r => setZones(r.data)).catch(() => setZones([]))
  }, [team, season])

  useEffect(() => {
    const params = [
      `metric=${metric}`,
      league ? `league=${encodeURIComponent(league)}` : '',
      season != null ? `year=${season}` : '',
      boardOrder ? `order=${boardOrder}` : '',
      `limit=${boardLimit}`,
    ].filter(Boolean).join('&')
    axios.get(`${API}/leaderboard?${params}`)
      .then(r => { setBoard(r.data.rows); setBoardMeta(r.data) })
      .catch(() => { setBoard([]); setBoardMeta(null) })
  }, [metric, league, season, boardOrder, boardLimit])

  const goals = shots.filter(s => s.result === 'Goal').length

  return (
    <div className="h-full flex flex-col">
      <header className="flex items-baseline justify-between px-6 py-4 border-b border-rule">
        <div>
          <span className="font-serif text-xl text-ink">OnTarget</span>
          <span className="font-serif text-xl text-muted"> / team analysis</span>
        </div>
        <span className="font-mono text-xs text-muted">top 5 leagues · 2020–2024</span>
      </header>

      <ResizablePanelGroup direction="horizontal" className="flex-1 min-h-0">
        <ResizablePanel defaultSize={32} minSize={22}>
          <div className="h-full flex flex-col bg-panel border-r border-rule overflow-hidden">
            <div className="flex-1 min-h-0 p-6">
              <p className="font-serif text-base text-muted leading-relaxed">
                Ask about form, finishing, pressing, or a specific fixture.
              </p>
            </div>
            <div className="p-4 border-t border-rule">
              <input
                placeholder="Why are Milan underperforming their xG?"
                className="w-full bg-transparent border border-rule rounded px-3 py-2 text-sm text-ink placeholder:text-faint focus:outline-none focus:border-muted"
              />
            </div>
          </div>
        </ResizablePanel>

        <ResizableHandle className="w-px bg-rule" />

        <ResizablePanel defaultSize={68}>
          <div className="h-full flex flex-col min-h-0 overflow-hidden">
            <div className="flex items-center justify-between px-8 border-b border-rule">
              <div className="flex gap-6">
                {TABS.map(t => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`font-mono text-xs py-3 border-b transition-colors ${
                      tab === t ? 'text-rust border-rust' : 'text-muted border-transparent hover:text-ink'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-3">
                <select
                  value={league}
                  onChange={e => setLeague(e.target.value)}
                  className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-xs text-muted focus:outline-none focus:border-muted"
                >
                  <option value="" className="bg-panel">all leagues</option>
                  {leagues.map(l => <option key={l} value={l} className="bg-panel">{l}</option>)}
                </select>

                <select
                  value={team}
                  onChange={e => setTeam(e.target.value)}
                  className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-xs text-muted focus:outline-none focus:border-muted"
                >
                  {teams.map(t => <option key={t} value={t} className="bg-panel">{t}</option>)}
                </select>

                <select
                  value={season ?? ''}
                  onChange={e => setSeason(e.target.value === '' ? null : Number(e.target.value))}
                  className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-xs text-muted focus:outline-none focus:border-muted"
                >
                  <option value="" className="bg-panel">all seasons</option>
                  {seasons.map(y => <option key={y} value={y} className="bg-panel">{y}</option>)}
                </select>
              </div>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden px-8 py-6">
              <h2 className="font-serif text-2xl text-ink mb-6">{team}</h2>

              {tab === 'form' && (
                <>
                  <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-3">
                    xG per match{leagueAvg != null && ` · league avg ${leagueAvg.toFixed(2)}`}
                  </div>
                  <div className="overflow-hidden">
                    {form.length > 0 ? <FormChart rows={form} leagueAvg={leagueAvg} /> : <Empty />}
                  </div>
                </>
              )}

              {tab === 'shots' && (
                <>
                  <div className="flex items-baseline justify-between mb-3">
                    <div className="font-mono text-[11px] uppercase tracking-wider text-faint">
                      {side} · {shots.length} shots · {goals} goals
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex gap-3">
                        {(['taken', 'conceded'] as const).map(s => (
                          <button
                            key={s}
                            onClick={() => setSide(s)}
                            className={`font-mono text-[11px] ${side === s ? 'text-rust' : 'text-muted hover:text-ink'}`}
                          >
                            {s}
                          </button>
                        ))}
                      </div>
                      <select
                        value={opponent}
                        onChange={e => setOpponent(e.target.value)}
                        className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-[11px] text-muted focus:outline-none focus:border-muted"
                      >
                        <option value="" className="bg-panel">all opponents</option>
                        {opponents.map(o => <option key={o} value={o} className="bg-panel">{o}</option>)}
                      </select>
                    </div>
                  </div>

                  <div className="overflow-hidden">
                    {loading
                      ? <div className="h-[420px] border-t border-rule opacity-40" />
                      : shots.length > 0 && <PitchMap shots={shots} />}
                  </div>

                  {quality.length === 0 ? <Empty /> : (
                    <>
                      <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-3 mt-8 border-t border-rule pt-6">
                        shot quality by game state
                      </div>
                      <div className="overflow-hidden mb-8">
                        <ShotQuality rows={quality} groupBy="game_state" />
                      </div>

                      <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-3">
                        shot quality by situation
                      </div>
                      <div className="overflow-hidden mb-8">
                        <ShotQuality rows={quality} groupBy="situation" />
                      </div>
                    </>
                  )}

                  {zones.length === 0 ? <Empty /> : (
                    <>
                      <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-3">
                        shot volume · zone × situation
                      </div>
                      <div className="overflow-hidden">
                        <ZoneMatrix rows={zones} />
                      </div>
                    </>
                  )}
                </>
              )}

              {tab === 'tags' && (tags === null ? <Empty /> : (
                <>
                  <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-3">
                    match tags · click a bar to see the matches
                  </div>
                  <div className="overflow-hidden mb-8">
                    <TagCounts data={tags} onSelect={setSelectedTag} />
                  </div>

                  {selectedTag && (
                    <div className="mb-8">
                      <div className="flex items-baseline justify-between mb-3 border-t border-rule pt-6">
                        <div className="font-serif text-lg text-ink">
                          {selectedTag.replace(/_/g, ' ')}
                          <span className="text-muted"> · {tagMatches.length} matches</span>
                        </div>
                        <button
                          onClick={() => { setSelectedTag(null); setSelectedMatch(null) }}
                          className="font-mono text-[11px] text-muted hover:text-ink"
                        >
                          clear
                        </button>
                      </div>

                      <div className="border-t border-rule">
                        {tagMatches.map(m => {
                          const isHome = m.home_team === team
                          const opp = isHome ? m.away_team : m.home_team
                          const active = selectedMatch?.match_id === m.match_id
                          return (
                            <div key={m.match_id} className="border-b border-rule">
                              <button
                                onClick={() => setSelectedMatch(active ? null : m)}
                                className={`w-full flex items-baseline justify-between py-2 text-left transition-colors ${
                                  active ? 'text-rust' : 'text-ink hover:text-rust'
                                }`}
                              >
                                <span className="font-mono text-xs text-muted w-24">{m.date.slice(0, 10)}</span>
                                <span className="flex-1 text-sm">{isHome ? 'vs' : 'at'} {opp}</span>
                                <span className="font-mono text-xs">
                                  {m.scored}–{m.missed}
                                  <span className="text-muted"> · xG {m.xG.toFixed(2)}–{m.xGA.toFixed(2)}</span>
                                </span>
                              </button>

                              {active && (
                                <div className="pb-6 pt-2">
                                  <div className="grid grid-cols-2 gap-6">
                                    <div>
                                      <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-2">
                                        {team} · {matchShots.length} shots
                                      </div>
                                      {matchShots.length > 0 && <PitchMap shots={matchShots} height={280} />}
                                    </div>
                                    <div>
                                      <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-2">
                                        {opp} · {oppShots.length} shots
                                      </div>
                                      {oppShots.length > 0 && <PitchMap shots={oppShots} height={280} />}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </>
              ))}

              {tab === 'players' && (
                <PlayersTab league={league || undefined} team={team || undefined} />
              )}

              {tab === 'profile' && (
                <>
                  {profile.length === 0 ? <Empty /> : (
                    <>
                      <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-3">
                        season profile · z-scores vs same league, same season
                      </div>
                      <div className="overflow-hidden mb-8">
                        <RadarChart rows={profile} season={season} />
                      </div>
                    </>
                  )}

                  {press.length === 0 ? <Empty /> : (
                    <>
                      <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-3">
                        press resistance vs finishing {season != null ? `· ${season}` : '· all seasons'}{league ? ` · ${league}` : ''}
                      </div>
                      <div className="overflow-hidden mb-8">
                        <PressScatter rows={press} highlight={team} />
                      </div>
                    </>
                  )}

                  {consistency.length === 0 ? <Empty /> : (
                    <>
                      <div className="font-mono text-[11px] uppercase tracking-wider text-faint mb-3">
                        attack xGD range across seasons {league ? `· ${league}` : '· all leagues'}
                      </div>
                      <div className="overflow-hidden">
                        <ConsistencyChart rows={consistency} highlight={team} />
                      </div>
                    </>
                  )}
                </>
              )}

              {tab === 'league' && (
                <>
                  <div className="flex items-baseline justify-between mb-3">
                    <div className="font-mono text-[11px] uppercase tracking-wider text-faint">
                      {boardMeta?.label ?? metric.replace(/_/g, ' ')} · {board.length} team-seasons
                    </div>
                    <select
                      value={metric}
                      onChange={e => setMetric(e.target.value)}
                      className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-[11px] text-muted focus:outline-none focus:border-muted"
                    >
                      {METRICS.map(m => (
                        <option key={m} value={m} className="bg-panel">{m.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                    <select value={boardOrder} onChange={e => setBoardOrder(e.target.value)}
                      className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-[11px] text-muted focus:outline-none focus:border-muted ml-2">
                      <option value="" className="bg-panel">best first</option>
                      <option value="desc" className="bg-panel">highest value</option>
                      <option value="asc" className="bg-panel">lowest value</option>
                    </select>
                    <select value={boardLimit} onChange={e => setBoardLimit(Number(e.target.value))}
                      className="bg-transparent border border-rule rounded px-2 py-1 font-mono text-[11px] text-muted focus:outline-none focus:border-muted ml-2">
                      {[10, 25, 50, 100].map(v => (
                        <option key={v} value={v} className="bg-panel">top {v}</option>
                      ))}
                    </select>
                  </div>
                  {boardMeta?.plain && (
                    <p className="font-serif text-sm text-muted leading-relaxed mb-4 max-w-prose">
                      {boardMeta.plain}
                    </p>
                  )}
                  <div className="overflow-hidden">
                    {board.length > 0 ? <Leaderboard rows={board} highlight={team} /> : <Empty />}
                  </div>
                </>
              )}
            </div>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
