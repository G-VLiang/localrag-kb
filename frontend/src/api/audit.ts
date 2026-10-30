import api from './client'

export interface AuditLog {
  id: string
  user_id: string | null
  action: string
  method: string
  path: string
  status_code: number
  ip: string | null
  created_at: string
}

export const listMyAudit = (limit = 50) => api.get<AuditLog[]>('/audit', { params: { limit } })

export const listAllAudit = (limit = 100, action?: string) =>
  api.get<AuditLog[]>('/audit/all', { params: { limit, ...(action ? { action } : {}) } })
