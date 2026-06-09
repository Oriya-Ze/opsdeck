const API_BASE = import.meta.env.VITE_API_URL || '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  getDashboardStats: () => request<import('../types').DashboardStats>('/dashboard/stats'),

  getNodes: () => request<import('../types').Node[]>('/nodes'),
  getNode: (id: string) => request<import('../types').Node>(`/nodes/${id}`),
  createNode: (data: import('../types').NodeCreate) =>
    request<import('../types').Node>('/nodes', { method: 'POST', body: JSON.stringify(data) }),
  updateNode: (id: string, data: import('../types').NodeUpdate) =>
    request<import('../types').Node>(`/nodes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteNode: (id: string) => request<void>(`/nodes/${id}`, { method: 'DELETE' }),
  runNodeHealthCheck: (id: string) =>
    request<import('../types').HealthCheck>(`/nodes/${id}/health-check`, { method: 'POST' }),
  runNodeAction: (id: string, action: string) =>
    request<import('../types').Job>(`/nodes/${id}/actions/${action}`, { method: 'POST' }),

  getServices: () => request<import('../types').Service[]>('/services'),
  getService: (id: string) => request<import('../types').Service>(`/services/${id}`),
  createService: (data: import('../types').ServiceCreate) =>
    request<import('../types').Service>('/services', { method: 'POST', body: JSON.stringify(data) }),
  updateService: (id: string, data: import('../types').ServiceUpdate) =>
    request<import('../types').Service>(`/services/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteService: (id: string) => request<void>(`/services/${id}`, { method: 'DELETE' }),
  runServiceHealthCheck: (id: string) =>
    request<import('../types').HealthCheck>(`/services/${id}/health-check`, { method: 'POST' }),

  getContainers: (nodeId?: string) =>
    request<import('../types').Container[]>(
      `/containers${nodeId ? `?node_id=${nodeId}` : ''}`,
    ),
  syncNodeContainers: (nodeId: string) =>
    request<import('../types').ContainerSyncResponse>(`/nodes/${nodeId}/sync-containers`, { method: 'POST' }),
  createContainer: (data: import('../types').ContainerCreate) =>
    request<import('../types').Container>('/containers', { method: 'POST', body: JSON.stringify(data) }),
  updateContainer: (id: string, data: import('../types').ContainerUpdate) =>
    request<import('../types').Container>(`/containers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteContainer: (id: string) => request<void>(`/containers/${id}`, { method: 'DELETE' }),

  getWorkloads: () => request<import('../types').Workload[]>('/workloads'),
  createWorkload: (data: import('../types').WorkloadCreate) =>
    request<import('../types').Workload>('/workloads', { method: 'POST', body: JSON.stringify(data) }),
  updateWorkload: (id: string, data: import('../types').WorkloadUpdate) =>
    request<import('../types').Workload>(`/workloads/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteWorkload: (id: string) => request<void>(`/workloads/${id}`, { method: 'DELETE' }),

  getJobs: () => request<import('../types').Job[]>('/jobs'),
  getJob: (id: string) => request<import('../types').Job>(`/jobs/${id}`),
  rerunJob: (id: string) => request<import('../types').Job>(`/jobs/${id}/rerun`, { method: 'POST' }),

  getHealthChecks: (params?: { target_type?: string; target_id?: string; limit?: number }) => {
    const q = new URLSearchParams()
    if (params?.target_type) q.set('target_type', params.target_type)
    if (params?.target_id) q.set('target_id', params.target_id)
    if (params?.limit) q.set('limit', String(params.limit))
    const qs = q.toString()
    return request<import('../types').HealthCheck[]>(`/health-checks${qs ? `?${qs}` : ''}`)
  },

  getActivityLogs: (limit = 50) =>
    request<import('../types').ActivityLog[]>(`/activity-logs?limit=${limit}`),

  getSshSettings: () => request<import('../types').SshSettings>('/settings/ssh'),
  saveSshSettings: (data: import('../types').SshSettingsSave) =>
    request<import('../types').SshSettings>('/settings/ssh', { method: 'PUT', body: JSON.stringify(data) }),
  deleteSshSettings: () => request<void>('/settings/ssh', { method: 'DELETE' }),
  testSshConnection: (data: import('../types').SshTestRequest) =>
    request<import('../types').SshTestResponse>('/settings/ssh/test', { method: 'POST', body: JSON.stringify(data) }),
  generateSshKey: () =>
    request<import('../types').SshGenerateResponse>('/settings/ssh/generate', { method: 'POST' }),

  testNodeConnection: (id: string) =>
    request<import('../types').NodeTestConnectionResponse>(`/nodes/${id}/test-connection`, { method: 'POST' }),
}
