import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend, LabelList } from 'recharts'
import { getSummary, listAnalyses, getModelInfo } from '../api'
import { Stat, Badge, Reveal, Icons, fmt, when, LEVEL_COLORS, ECO_HEX, CHART } from '../components/common'

const tip = { background: CHART.tooltipBg, border: `1px solid ${CHART.tooltipBorder}`, borderRadius: 10, fontSize: 13 }

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [recent, setRecent] = useState([])
  const [model, setModel] = useState(null)

  useEffect(() => {
    getSummary().then((r) => setSummary(r.data)).catch(() => {})
    listAnalyses({ limit: 5 }).then((r) => setRecent(r.data)).catch(() => {})
    getModelInfo().then((r) => setModel(r.data)).catch(() => {})
  }, [])

  const total = summary?.total_analyses ?? 0
  const pie = summary ? Object.entries(summary.level_distribution).map(([name, value]) => ({ name, value })) : []
  const mm = model?.metrics   // XGBoost accuracy / precision / recall / f1
  const cmp = model?.comparison
  const cmpData = cmp ? [
    { metric: 'Accuracy', Before: +(cmp.before.accuracy * 100).toFixed(0), After: +(cmp.after.accuracy * 100).toFixed(0) },
    { metric: 'Macro-F1', Before: +(cmp.before.f1_macro * 100).toFixed(0), After: +(cmp.after.f1_macro * 100).toFixed(0) },
  ] : []

  return (
    <>
      <h1>Dashboard</h1>
      <p className="sub">Congestion, emissions and carbon-limit compliance across all analysed footage.</p>

      <div className="grid cols-4">
        <Stat label="Analyses" icon={<Icons.spark />} countTo={total} delay={0} hint={`${summary?.locations ?? 0} locations`} />
        <Stat label="Avg vehicles / frame" icon={<Icons.car />} countTo={summary?.avg_vehicles ?? 0} decimals={1} delay={80} />
        <Stat label="CO₂ · kg / hour" icon={<Icons.cloud />} countTo={summary?.total_co2_kg_per_hour ?? 0} decimals={0} delay={160} hint="All sites" />
        <Stat label="Within carbon limit" icon={<Icons.leaf />} delay={240}
          value={summary ? `${summary.within_limit}/${total}` : '—'}
          hint={summary ? `${summary.pct_within_limit}% under ${summary.carbon_limit_kg_per_hour.toLocaleString()} kg/h cap` : ''} />
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Reveal delay={60} className="card lift">
          <h2>Carbon-limit compliance</h2>
          {total ? (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginTop: 8 }}>
                <span style={{ fontSize: 52, fontWeight: 800, fontFamily: 'Sora, sans-serif', letterSpacing: '-0.03em',
                  color: summary.pct_within_limit >= 50 ? ECO_HEX.green : ECO_HEX.red }}>{summary.pct_within_limit}%</span>
                <span className="muted">within limit</span>
              </div>
              <div className="eco-meter" style={{ height: 16, marginTop: 18 }}>
                <div style={{ width: `${summary.pct_within_limit}%`, background: ECO_HEX.green }} />
              </div>
              <div className="legend" style={{ justifyContent: 'space-between' }}>
                <span className="item"><span className="dot" style={{ background: ECO_HEX.green }} /><b>{summary.within_limit}</b> within limit</span>
                <span className="item"><span className="dot" style={{ background: ECO_HEX.red }} /><b>{summary.over_limit}</b> over limit</span>
              </div>
            </>
          ) : <p className="muted">Eco-friendliness appears once a video is analysed.</p>}
        </Reveal>

        <Reveal delay={140} className="card lift">
          <h2>Congestion distribution</h2>
          {total ? (
            <>
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={pie} dataKey="value" nameKey="name" innerRadius={62} outerRadius={92} paddingAngle={4} stroke="none" animationDuration={900}>
                      {pie.map((p) => <Cell key={p.name} fill={LEVEL_COLORS[p.name]} />)}
                    </Pie>
                    <Tooltip contentStyle={tip} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="donut-center">
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 28, fontWeight: 800, fontFamily: 'Sora, sans-serif' }}>{total}</div>
                    <div className="muted" style={{ fontSize: 11 }}>analyses</div>
                  </div>
                </div>
              </div>
              <div className="legend" style={{ justifyContent: 'center' }}>
                {pie.map((p) => (
                  <span className="item" key={p.name}>
                    <span className="dot" style={{ background: LEVEL_COLORS[p.name] }} />{p.name} <b>{p.value}</b>
                  </span>
                ))}
              </div>
            </>
          ) : <p className="muted">No analyses yet. <Link to="/analyze" style={{ color: 'var(--accent)' }}>Upload a video →</Link></p>}
        </Reveal>
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Reveal delay={60} className="card lift">
          <h2>Before vs after XGBoost <span className="muted" style={{ fontWeight: 400, fontSize: 12 }}>· taller is better</span></h2>
          {cmpData.length ? (
            <ResponsiveContainer width="100%" height={236}>
              <BarChart data={cmpData} barGap={8} margin={{ top: 18 }}>
                <CartesianGrid stroke={CHART.grid} vertical={false} />
                <XAxis dataKey="metric" stroke={CHART.axis} fontSize={13} tickLine={false} axisLine={false} />
                <YAxis stroke={CHART.axis} fontSize={12} domain={[0, 100]} unit="%" tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tip} cursor={{ fill: 'rgba(52,211,153,0.06)' }} formatter={(v) => `${v}%`} />
                <Legend />
                <Bar dataKey="Before" name="Before (rule-based)" fill="#5f766a" radius={[6, 6, 0, 0]} animationDuration={900}>
                  <LabelList dataKey="Before" position="top" formatter={(v) => `${v}%`} fill="#8ba394" fontSize={12} />
                </Bar>
                <Bar dataKey="After" name="After (XGBoost)" fill="#34d399" radius={[6, 6, 0, 0]} animationDuration={1100}>
                  <LabelList dataKey="After" position="top" formatter={(v) => `${v}%`} fill="#eaf3ec" fontSize={12} fontWeight={600} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="muted">Train the model to see the before/after comparison.</p>}
        </Reveal>

        <Reveal delay={140} className="card lift">
          <h2>XGBoost metrics <span className="muted" style={{ fontWeight: 400, fontSize: 12 }}>· on test data</span></h2>
          {mm ? (
            <div className="metric-grid">
              {[['Accuracy', mm.accuracy], ['Precision', mm.precision_macro], ['Recall', mm.recall_macro], ['F1-score', mm.f1_macro]].map(([k, v]) => (
                <div className="metric" key={k}>
                  <div className="mk">{k}</div>
                  <div className="mv">{v != null ? `${(v * 100).toFixed(1)}%` : '—'}</div>
                </div>
              ))}
            </div>
          ) : <p className="muted">Train the model to see its metrics.</p>}
          {mm && <p className="muted" style={{ fontSize: 12, marginTop: 12 }}>Macro-averaged across Low / Moderate / High on {mm.n_test} held-out samples.</p>}
        </Reveal>
      </div>

      <Reveal delay={60} className="card lift" style={{ marginTop: 16 }}>
        <h2>Recent analyses</h2>
        <table>
          <thead><tr><th>When</th><th>Location</th><th>Vehicles</th><th>Congestion</th><th>Conf.</th><th>kg CO₂ / h</th></tr></thead>
          <tbody>
            {recent.map((a) => (
              <tr key={a.id}>
                <td className="muted">{when(a.created_at)}</td>
                <td><b>{a.location}</b></td>
                <td>{fmt(a.avg_vehicles)}</td>
                <td>{a.status === 'done' ? <Badge level={a.congestion_level} /> : <span className="badge failed">{a.status}</span>}</td>
                <td>{a.congestion_confidence ? `${Math.round(a.congestion_confidence * 100)}%` : '—'}</td>
                <td>{fmt(a.co2_kg_per_hour)}</td>
              </tr>
            ))}
            {!recent.length && <tr><td colSpan={6} className="muted">Nothing yet. <Link to="/analyze" style={{ color: 'var(--accent)' }}>Analyze a video →</Link></td></tr>}
          </tbody>
        </table>
      </Reveal>
    </>
  )
}
