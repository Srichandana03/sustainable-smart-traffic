import { useEffect, useState } from 'react'
import { listAnalyses, deleteAnalysis } from '../api'
import { Badge, Reveal, Icons, fmt, when } from '../components/common'

export default function History() {
  const [rows, setRows] = useState([])
  const [filter, setFilter] = useState('')
  const load = () => listAnalyses({ limit: 200 }).then((r) => setRows(r.data))
  useEffect(() => { load() }, [])

  const locations = [...new Set(rows.map((r) => r.location))]
  const shown = filter ? rows.filter((r) => r.location === filter) : rows

  const remove = async (id) => {
    if (!confirm('Delete this analysis and its video?')) return
    await deleteAnalysis(id); load()
  }

  const exportCsv = () => {
    const head = ['id', 'created_at', 'location', 'latitude', 'longitude', 'avg_vehicles', 'max_vehicles', 'congestion_level', 'confidence', 'co2_kg_per_hour', 'detector']
    const lines = shown.map((a) => [a.id, a.created_at, a.location, a.latitude, a.longitude, a.avg_vehicles, a.max_vehicles, a.congestion_level, a.congestion_confidence, a.co2_kg_per_hour, a.detector_backend]
      .map((v) => `"${v ?? ''}"`).join(','))
    const blob = new Blob([[head.join(','), ...lines].join('\n')], { type: 'text/csv' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'ecopath_analyses.csv'; a.click()
  }

  return (
    <>
      <h1>History</h1>
      <p className="sub">Every analysis run, with the option to export for reports.</p>
      <Reveal className="card lift">
        <div className="row" style={{ marginBottom: 14, justifyContent: 'space-between' }}>
          <div className="field" style={{ margin: 0 }}>
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="">All locations</option>
              {locations.map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <button className="btn ghost sm" onClick={exportCsv}><Icons.download width={15} height={15} /> Export CSV</button>
        </div>
        <table>
          <thead><tr><th>When</th><th>Location</th><th>File</th><th>Vehicles</th><th>Congestion</th><th>kg CO₂ / h</th><th></th></tr></thead>
          <tbody>
            {shown.map((a) => (
              <tr key={a.id}>
                <td className="muted">{when(a.created_at)}</td>
                <td><b>{a.location}</b></td>
                <td className="muted">{a.filename}</td>
                <td>{fmt(a.avg_vehicles)}</td>
                <td>{a.status === 'done' ? <Badge level={a.congestion_level} /> : <span className="badge failed" title={a.error}>{a.status}</span>}</td>
                <td>{fmt(a.co2_kg_per_hour)}</td>
                <td><button className="btn ghost sm" onClick={() => remove(a.id)}><Icons.trash width={15} height={15} /></button></td>
              </tr>
            ))}
            {!shown.length && <tr><td colSpan={7} className="muted">No analyses.</td></tr>}
          </tbody>
        </table>
      </Reveal>
    </>
  )
}
