import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { auth } from '../api'
import { Icons } from './common'

export default function Layout() {
  const nav = useNavigate()
  const loc = useLocation()
  const user = auth.user()
  const name = user?.full_name || user?.email || 'Planner'
  const initial = name.trim().charAt(0).toUpperCase()

  const links = [
    { to: '/', end: true, label: 'Dashboard', icon: <Icons.dashboard /> },
    { to: '/analyze', label: 'Analyze video', icon: <Icons.analyze /> },
    { to: '/hotspots', label: 'Hotspots', icon: <Icons.hotspot /> },
    { to: '/history', label: 'History', icon: <Icons.history /> },
  ]

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="leaf"><Icons.leaf width={17} height={17} /></span>
          Eco<span className="grad-text">Path</span>
        </div>
        <nav className="nav">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end}>{l.icon}<span>{l.label}</span></NavLink>
          ))}
        </nav>
        <div className="user">
          <div className="who">
            <span className="avatar">{initial}</span>
            <span className="meta"><b>{name}</b><span className="role">Signed in</span></span>
          </div>
          <button className="btn ghost sm signout" onClick={() => { auth.logout(); nav('/login') }}>
            <Icons.logout width={15} height={15} /> Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <div key={loc.pathname} className="page-enter"><Outlet /></div>
      </main>
    </div>
  )
}
