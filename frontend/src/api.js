import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem('ecopath_token')
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !err.config.url.includes('/auth/')) {
      localStorage.removeItem('ecopath_token')
      localStorage.removeItem('ecopath_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export const auth = {
  async login(email, password) {
    const form = new URLSearchParams({ username: email, password })
    const { data } = await api.post('/auth/login', form)
    localStorage.setItem('ecopath_token', data.access_token)
    localStorage.setItem('ecopath_user', JSON.stringify(data.user))
    return data.user
  },
  register: (email, password, full_name) => api.post('/auth/register', { email, password, full_name }),
  logout() {
    localStorage.removeItem('ecopath_token')
    localStorage.removeItem('ecopath_user')
  },
  user: () => JSON.parse(localStorage.getItem('ecopath_user') || 'null'),
}

export const analyze = (file, location, latitude, longitude, onProgress) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('location', location)
  if (latitude) fd.append('latitude', latitude)
  if (longitude) fd.append('longitude', longitude)
  return api.post('/analyze', fd, { onUploadProgress: onProgress, timeout: 600000 })
}
export const listAnalyses = (params) => api.get('/analyses', { params })
export const getAnalysis = (id) => api.get(`/analyses/${id}`)
export const deleteAnalysis = (id) => api.delete(`/analyses/${id}`)
export const getSummary = () => api.get('/summary')
export const getHotspots = () => api.get('/hotspots')
export const getForecast = (location, horizon_hours = 6) => api.get('/forecast', { params: { location, horizon_hours } })
export const getModelInfo = () => api.get('/model/info')
