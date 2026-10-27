import { useEffect, useRef, useState } from 'react'

/* ---------- inline icon set (no icon dependency) ---------- */
const S = { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.9, strokeLinecap: 'round', strokeLinejoin: 'round' }
export const Icons = {
  dashboard: (p) => <svg {...S} {...p}><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></svg>,
  analyze: (p) => <svg {...S} {...p}><path d="M15 10l-4 4-2-2-4 4" /><rect x="3" y="3" width="18" height="18" rx="2.5" /></svg>,
  video: (p) => <svg {...S} {...p}><rect x="2" y="5" width="14" height="14" rx="2.5" /><path d="m16 9 6-3v12l-6-3" /></svg>,
  hotspot: (p) => <svg {...S} {...p}><path d="M12 2C8 2 5 5 5 9c0 5 7 13 7 13s7-8 7-13c0-4-3-7-7-7Z" /><circle cx="12" cy="9" r="2.5" /></svg>,
  history: (p) => <svg {...S} {...p}><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 4v4h4" /><path d="M12 8v4l3 2" /></svg>,
  leaf: (p) => <svg {...S} {...p}><path d="M11 20A7 7 0 0 1 4 13c0-6 7-9 15-9 0 8-3 15-9 15Z" /><path d="M4 20c2-4 5-6 9-7" /></svg>,
  car: (p) => <svg {...S} {...p}><path d="M5 11l1.5-4A2 2 0 0 1 8.4 6h7.2a2 2 0 0 1 1.9 1.3L19 11" /><path d="M3 13h18v4a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1v-1H6v1a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z" /><circle cx="7" cy="15" r="0.6" /><circle cx="17" cy="15" r="0.6" /></svg>,
  cloud: (p) => <svg {...S} {...p}><path d="M7 18a4 4 0 1 1 .7-7.9A5 5 0 0 1 18 11a3.5 3.5 0 0 1-.5 7Z" /></svg>,
  cpu: (p) => <svg {...S} {...p}><rect x="7" y="7" width="10" height="10" rx="2" /><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" /></svg>,
  logout: (p) => <svg {...S} {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="m16 17 5-5-5-5" /><path d="M21 12H9" /></svg>,
  download: (p) => <svg {...S} {...p}><path d="M12 3v12" /><path d="m7 10 5 5 5-5" /><path d="M5 21h14" /></svg>,
  trash: (p) => <svg {...S} {...p}><path d="M4 7h16M10 11v6M14 11v6M5 7l1 13a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-13M9 7V4h6v3" /></svg>,
  spark: (p) => <svg {...S} {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" /></svg>,
}

/* ---------- animated count-up for numeric stats ---------- */
export function useCountUp(target, { duration = 900, decimals = 0 } = {}) {
  const [val, setVal] = useState(0)
  const ref = useRef()
  useEffect(() => {
    const end = Number(target)
    if (!isFinite(end)) { setVal(target); return }
    const start = performance.now()
    cancelAnimationFrame(ref.current)
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      setVal(+(end * eased).toFixed(decimals))
      if (t < 1) ref.current = requestAnimationFrame(tick)
    }
    ref.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(ref.current)
  }, [target, duration, decimals])
  return val
}

/* ---------- badges ---------- */
export const Badge = ({ level }) => <span className={`badge ${level}`}>{level}</span>
export const EcoBadge = ({ eco }) =>
  eco ? <span className={`badge eco-${eco.color}`}>{eco.status}</span> : <span className="badge">—</span>

/* ---------- animated stat card ---------- */
export const Stat = ({ label, value, hint, icon, delay = 0, countTo, decimals = 0, suffix = '' }) => {
  const animated = countTo != null
  const counted = useCountUp(animated ? countTo : 0, { decimals })  // hook always called (rules of hooks)
  const shown = animated ? counted : value
  return (
    <div className="card stat lift reveal" style={{ animationDelay: `${delay}ms` }}>
      {icon && <div className="ic">{icon}</div>}
      <div className="label">{label}</div>
      <div className="value">{animated ? `${Number(shown).toLocaleString()}${suffix}` : value}</div>
      {hint && <div className="hint">{hint}</div>}
    </div>
  )
}

/* ---------- reveal wrapper (staggered entrance) ---------- */
export const Reveal = ({ children, delay = 0, className = '', style = {}, ...rest }) => (
  <div className={`reveal ${className}`} style={{ animationDelay: `${delay}ms`, ...style }} {...rest}>{children}</div>
)

export const fmt = (n, d = 1) => (n == null ? '—' : Number(n).toFixed(d))
export const when = (iso) => new Date(iso).toLocaleString()

export const LEVEL_COLORS = { Low: '#4ade80', Moderate: '#fbbf24', High: '#fb7185' }
export const CLASS_COLORS = { car: '#60a5fa', motorcycle: '#a78bfa', bus: '#fb923c', truck: '#f472b6' }
export const ECO_HEX = { green: '#4ade80', amber: '#fbbf24', red: '#fb7185' }
export const CHART = { grid: '#223029', axis: '#8ba394', tooltipBg: '#141c17', tooltipBorder: '#243a2e' }
