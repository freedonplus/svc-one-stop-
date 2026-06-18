const API_BASE = 'http://localhost:8710'

async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export function fetchServices() {
  return request('/api/services')
}

export function addService(service) {
  return request('/api/services', {
    method: 'POST',
    body: JSON.stringify(service),
  })
}

export function updateService(id, data) {
  return request(`/api/services/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function deleteService(id) {
  return request(`/api/services/${id}`, {
    method: 'DELETE',
  })
}

export function startService(id) {
  return request(`/api/services/${id}/start`, { method: 'POST' })
}

export function stopService(id) {
  return request(`/api/services/${id}/stop`, { method: 'POST' })
}

export function batchStart(ids) {
  return request('/api/services/batch/start', {
    method: 'POST',
    body: JSON.stringify(ids),
  })
}

export function batchStop(ids) {
  return request('/api/services/batch/stop', {
    method: 'POST',
    body: JSON.stringify(ids),
  })
}

export function healthCheck() {
  return request('/api/health')
}

export function fetchLogs(id, lines = 200) {
  return request(`/api/services/${id}/logs?lines=${lines}`)
}

export function clearLogs(id) {
  return request(`/api/services/${id}/logs`, { method: 'DELETE' })
}
