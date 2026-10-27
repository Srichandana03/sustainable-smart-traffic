import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts'
import { getHotspots, getForecast } from '../api'
import { fmt, Badge, Reveal, CHART } from '../components/common'

const tip = { background: CHART.tooltipBg, border: `1px solid ${CHART.tooltipBorder}`, borderRadius: 10 }

export default function Hotspots() {
  const [rows, setRows] = useState([])
  const [sel, setSel] = useState(null)
  const [fc, setFc] = useState([])

  useEffect(() => { getHotspots().then((r) => { setRows(r.data); if (r.data[0]) setSel(r.data[0].location) }) }, [])
  useEffect(() => { if (sel) getForecast(sel, 8).then((r) => setFc(r.data)) }, [sel])

  return (
    <>
      <h1>Congestion hotspots</h1>
      <p className="sub">Locations ranked by congestion frequency and CO₂. Click a row to forecast it.</p>

      <Reveal className="card lift">
        <table>
          <thead><tr><th>#</th><th>Location</th><th>Samples</th><th>High-congestion rate</th><th>Avg kg CO₂ / h</th><th>Score</th><th>Coords</th></tr></thead>
          <tbody>
            {rows.map((h) => (
              <tr key={h.location} onClick={() => setSel(h.location)}
                style={{ cursor: 'pointer', background: sel === h.location ? 'rgba(52,211,153,0.08)' : undefined,
                  boxShadow: sel === h.location ? 'inset 3px 0 0 var(--accent)' : undefined }}>
                <td style={{ fontFamily: 'Sora, sans-serif', fontWeight: 700, color: 'var(--accent)' }}>{h.rank}</td>
                <td><b>{h.location}</b></td>
                <td>{h.samples}</td>
                <td>{Math.round(h.high_frequency * 100)}%</td>
                <td>{fmt(h.avg_co2_kg_per_hour)}</td>
                <td>
                  <div className="row"><div className="score-bar" style={{ width: 90 }}><div style={{ width: `${h.score}%` }} /></div>{h.score}</div>
                </td>
                <td className="muted">{h.latitude != null ? `${h.latitude}, ${h.longitude}` : '—'}</td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={7} className="muted">Analyse a few videos across locations to see hotspots.</td></tr>}
          </tbody>
        </table>
      </Reveal>

      {sel && (
        <Reveal className="card lift" delay={120} style={{ marginTop: 16 }} key={sel}>
          <h2>Expected congestion · next 8 h — {sel} <span className="muted" style={{ fontWeight: 400, fontSize: 12 }}>· baseline estimate</span></h2>
          <ResponsiveContainer width="100%" height={230}>
            <LineChart data={fc.map((p) => ({ ...p, t: p.time.slice(11, 16) }))}>
              <CartesianGrid stroke={CHART.grid} />
              <XAxis dataKey="t" stroke={CHART.axis} fontSize={12} tickLine={false} axisLine={false} />
              <YAxis domain={[0, 1]} stroke={CHART.axis} fontSize={12} tickLine={false} axisLine={false}
                tickFormatter={(v) => (v < 0.3 ? 'Low' : v < 0.7 ? 'Mod' : 'High')} ticks={[0.15, 0.5, 0.85]} />
              <ReferenceLine y={0.3} stroke="#fbbf24" strokeDasharray="4 4" />
              <ReferenceLine y={0.7} stroke="#fb7185" strokeDasharray="4 4" />
              <Tooltip contentStyle={tip} formatter={(v, n, p) => [p.payload.level, 'Expected']} />
              <Line type="monotone" dataKey="score" stroke="#34d399" strokeWidth={2.5} dot={{ r: 3, fill: '#34d399' }} animationDuration={900} />
            </LineChart>
          </ResponsiveContainer>
          <div className="row" style={{ flexWrap: 'wrap', gap: 10, marginTop: 6 }}>
            {fc.map((p) => <span key={p.time} className="muted" style={{ fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 5 }}>{p.time.slice(11, 16)} <Badge level={p.level} /></span>)}
          </div>
        </Reveal>
      )}
    </>
  )
}
