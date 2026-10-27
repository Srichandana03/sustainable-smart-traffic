import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { auth } from '../api'
import { Icons } from '../components/common'

export default function Login() {
  const nav = useNavigate()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setErr(''); setBusy(true)
    try {
      if (mode === 'register') await auth.register(email, password, name)
      await auth.login(email, password)
      nav('/')
    } catch (ex) {
      setErr(ex.response?.data?.detail || 'Something went wrong')
    } finally { setBusy(false) }
  }

  return (
    <div className="auth">
      <div className="auth-hero">
        <span className="orb a" /><span className="orb b" /><span className="orb c" />
        <div className="auth-hero-content">
          <div className="brand" style={{ fontSize: 24 }}>
            <span className="leaf"><Icons.leaf width={17} height={17} /></span>
            Eco<span className="grad-text">Path</span>
          </div>
          <h2>See the city breathe.</h2>
          <p>Turn traffic footage into congestion insight and CO₂ emission intelligence — and know, at a glance, whether each junction stays within the carbon limit.</p>
        </div>
      </div>

      <div className="auth-form-wrap">
        <form className="auth-card" onSubmit={submit}>
          <div className="brand">
            <span className="leaf"><Icons.leaf width={17} height={17} /></span>
            Eco<span className="grad-text">Path</span>
          </div>
          <p className="sub" style={{ margin: '4px 0 0' }}>
            {mode === 'login' ? 'Welcome back — sign in to continue.' : 'Create your planner account.'}
          </p>

          <div className="auth-tabs">
            <span className="slider" style={{ transform: `translateX(${mode === 'login' ? 0 : '100%'})` }} />
            <button type="button" className={mode === 'login' ? 'on' : ''} onClick={() => { setMode('login'); setErr('') }}>Sign in</button>
            <button type="button" className={mode === 'register' ? 'on' : ''} onClick={() => { setMode('register'); setErr('') }}>Register</button>
          </div>

          {mode === 'register' && (
            <div className="field reveal"><label>Full name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Planner" /></div>
          )}
          <div className="field"><label>Email</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="planner@city.gov" /></div>
          <div className="field"><label>Password</label>
            <input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 6 characters" /></div>

          {err && <div className="error">{err}</div>}
          <button className="btn" disabled={busy} style={{ width: '100%', marginTop: 4 }}>
            {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>
      </div>
    </div>
  )
}
