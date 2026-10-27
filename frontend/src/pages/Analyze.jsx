import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, BarChart, Bar, Cell, LabelList } from 'recharts'
import { analyze } from '../api'
import { Badge, EcoBadge, Reveal, Icons, fmt, CLASS_COLORS, ECO_HEX, CHART } from '../components/common'

const tip = { background: CHART.tooltipBg, border: `1px solid ${CHART.tooltipBorder}`, borderRadius: 10 }

export default function Analyze() {
  const [file, setFile] = useState(null)
  const [location, setLocation] = useState('')
  const [lat, setLat] = useState('')
  const [lon, setLon] = useState('')
  const [progress, setProgress] = useState(0)
  const [phase, setPhase] = useState('') // uploading | analysing
  const [result, setResult] = useState(null)
  const [err, setErr] = useState('')
  const [drag, setDrag] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!file) return setErr('Choose a video first')
    setErr(''); setResult(null); setPhase('uploading'); setProgress(0)
    try {
      const { data } = await analyze(file, location, lat, lon, (ev) => {
        const p = Math.round((ev.loaded / ev.total) * 100)
        setProgress(p); if (p === 100) setPhase('analysing')
      })
      setResult(data)
    } catch (ex) {
      setErr(ex.response?.data?.detail || ex.message)
    } finally { setPhase('') }
  }

  const stats = result?.details?.stats
  const pred = result?.details?.prediction
  const emis = result?.details?.emissions
  const eco = result?.details?.sustainability
  const series = stats?.per_frame_counts?.map((c, i) => ({ i, vehicles: c })) || []
  const byClass = stats ? Object.entries(stats.counts_by_class).map(([k, v]) => ({ cls: k, avg: v, co2: emis?.co2_kg_by_class?.[k] ?? 0 })) : []

  return (
    <>
      <h1>Analyze traffic video</h1>
      <p className="sub">Detect vehicles, classify congestion, estimate CO₂ and score it against the carbon limit.</p>

      <div className="grid cols-2">
        <Reveal className="card" delay={0}>
          <form onSubmit={submit}>
            <div
              className={`dropzone ${drag ? 'active' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => { e.preventDefault(); setDrag(false); setFile(e.dataTransfer.files[0]) }}
              onClick={() => document.getElementById('f').click()}
            >
              <div className="dz-ic"><Icons.video width={22} height={22} /></div>
              {file
                ? <b style={{ color: 'var(--text)' }}>{file.name}</b>
                : <>Drop a video here or <span style={{ color: 'var(--accent)' }}>click to browse</span><div className="muted" style={{ fontSize: 12, marginTop: 4 }}>.mp4 · .avi · .mov · .mkv · .webm</div></>}
              <input id="f" type="file" accept="video/*" hidden onChange={(e) => setFile(e.target.files[0])} />
            </div>
            <div style={{ height: 16 }} />
            <div className="field"><label>Location / junction name</label>
              <input required value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Hitec City Junction" /></div>
            <div className="row">
              <div className="field" style={{ flex: 1 }}><label>Latitude (optional)</label><input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="17.45" /></div>
              <div className="field" style={{ flex: 1 }}><label>Longitude (optional)</label><input value={lon} onChange={(e) => setLon(e.target.value)} placeholder="78.38" /></div>
            </div>
            {phase && (
              <>
                <div className="progress"><div style={{ width: `${phase === 'analysing' ? 100 : progress}%` }} /></div>
                <p className="muted" style={{ fontSize: 13 }}>{phase === 'uploading' ? `Uploading… ${progress}%` : 'Running detection & models… this can take a minute.'}</p>
              </>
            )}
            {err && <div className="error">{err}</div>}
            <button className="btn" disabled={!!phase} style={{ width: '100%' }}>
              <Icons.spark width={16} height={16} /> {phase ? 'Working…' : 'Run analysis'}
            </button>
          </form>
        </Reveal>

        <Reveal className="card" delay={100}>
          <h2>Result</h2>
          {!result && !phase && <p className="muted">Results appear here after the analysis finishes.</p>}
          {phase && (
            <div className="stagger">
              <div className="skel big" /><div className="skel line" style={{ width: '90%' }} />
              <div className="skel line" style={{ width: '80%' }} /><div className="skel line" style={{ width: '70%' }} />
            </div>
          )}
          {result && result.status === 'failed' && <div className="error">Analysis failed: {result.error}</div>}
          {result && result.status === 'done' && (
            <>
              <div style={{ fontSize: 34, fontWeight: 700, margin: '4px 0 14px', display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <Badge level={result.congestion_level} />
                <span className="muted" style={{ fontSize: 14 }}>{Math.round(result.congestion_confidence * 100)}% confidence · {pred.model}</span>
              </div>
              <div className="result-kv">
                <b>Location</b><span>{result.location}</span>
                <b>Detector</b><span>{result.detector_backend}</span>
                <b>Frames analysed</b><span>{stats.frames_analyzed} / {stats.frames_total}</span>
                <b>Avg vehicles / frame</b><span>{fmt(result.avg_vehicles)} (max {result.max_vehicles})</span>
                <b>Road coverage</b><span>{fmt(stats.density * 100)}%</span>
                <b>CO₂ / hour</b><span><b style={{ color: 'var(--high)' }}>{fmt(emis.co2_kg_per_hour)} kg</b></span>
                <b>Free-flow baseline</b><span>{fmt(emis.co2_kg_per_hour_free_flow)} kg / h</span>
                <b>Excess from congestion</b><span>{fmt(emis.excess_due_to_congestion_kg_per_hour)} kg / h (×{emis.congestion_multiplier})</span>
              </div>

              {eco && (
                <div className="eco-panel">
                  <div className="eco-top">
                    <div>
                      <div className="muted" style={{ fontSize: 11.5, textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600 }}>Sustainability</div>
                      <div style={{ fontSize: 20, fontWeight: 700, marginTop: 5, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <EcoBadge eco={eco} />
                        <span className="muted" style={{ fontSize: 13 }}>{eco.percent_of_limit}% of limit</span>
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', fontSize: 13 }}>
                      <div><b style={{ color: ECO_HEX[eco.color], fontSize: 18, fontFamily: 'Sora, sans-serif' }}>{fmt(eco.co2_kg_per_hour, 0)}</b> kg CO₂ / h</div>
                      <div className="muted">limit {eco.carbon_limit_kg_per_hour.toLocaleString()} kg / h</div>
                    </div>
                  </div>
                  <div className="eco-meter">
                    <div style={{ width: `${Math.min(eco.percent_of_limit, 100)}%`, background: ECO_HEX[eco.color] }} />
                  </div>
                  <div className="eco-scale"><span>0</span><span>carbon limit →</span></div>
                  <div className="eco-msg">{eco.message}</div>
                </div>
              )}

              <div style={{ marginTop: 16 }}>
                <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>Class probabilities</div>
                {Object.entries(pred.probabilities).map(([k, v]) => (
                  <div key={k} className="row" style={{ fontSize: 13, marginBottom: 6 }}>
                    <span style={{ width: 76 }}>{k}</span>
                    <div className="score-bar" style={{ flex: 1 }}><div style={{ width: `${v * 100}%` }} /></div>
                    <span style={{ width: 40, textAlign: 'right' }}>{Math.round(v * 100)}%</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </Reveal>
      </div>

      {result?.status === 'done' && (
        <div className="grid cols-2" style={{ marginTop: 16 }}>
          <Reveal className="card lift" delay={80}>
            <h2>Vehicles over the clip</h2>
            <ResponsiveContainer width="100%" height={230}>
              <LineChart data={series}>
                <defs>
                  <linearGradient id="vg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#34d399" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={CHART.grid} />
                <XAxis dataKey="i" stroke={CHART.axis} fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke={CHART.axis} fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tip} />
                <Line type="monotone" dataKey="vehicles" stroke="#34d399" dot={false} strokeWidth={2.5} fill="url(#vg)" animationDuration={900} />
              </LineChart>
            </ResponsiveContainer>
          </Reveal>
          <Reveal className="card lift" delay={160}>
            <h2>CO₂ by vehicle type <span className="muted" style={{ fontWeight: 400, fontSize: 12 }}>· kg / window</span></h2>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={byClass} margin={{ top: 18 }}>
                <CartesianGrid stroke={CHART.grid} vertical={false} />
                <XAxis dataKey="cls" stroke={CHART.axis} fontSize={12.5} tickLine={false} axisLine={false} />
                <YAxis stroke={CHART.axis} fontSize={12} tickLine={false} axisLine={false} unit=" kg" width={48} />
                <Tooltip contentStyle={tip} cursor={{ fill: 'rgba(52,211,153,0.06)' }} formatter={(v) => [`${fmt(v, 2)} kg`, 'CO₂']} />
                <Bar dataKey="co2" name="kg CO₂" radius={[6, 6, 0, 0]} animationDuration={1000}>
                  {byClass.map((b) => <Cell key={b.cls} fill={CLASS_COLORS[b.cls]} />)}
                  <LabelList dataKey="co2" position="top" formatter={(v) => (v ? fmt(v, 1) : '')} fill="#bfd0c6" fontSize={11} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Reveal>
        </div>
      )}
    </>
  )
}
