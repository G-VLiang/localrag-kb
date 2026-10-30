import api from './client'
import type { DocNode, Document, KnowledgeBase, Space, User } from './types'

// Auth
export const register = (data: { email: string; username: string; password: string }) =>
  api.post<User>('/auth/register', data)

export const login = (email: string, password: string) => {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', password)
  return api.post<{ access_token: string; refresh_token: string }>('/auth/login', form)
}

export const getMe = () => api.get<User>('/auth/me')

// Spaces
export const listSpaces = () => api.get<Space[]>('/spaces')
export const createSpace = (data: { name: string; description?: string; kind: string }) =>
  api.post<Space>('/spaces', data)

// Knowledge bases
export const listKB = (spaceId: string) => api.get<KnowledgeBase[]>(`/spaces/${spaceId}/kb`)
export const createKB = (spaceId: string, data: { name: string; description?: string }) =>
  api.post<KnowledgeBase>(`/spaces/${spaceId}/kb`, data)

// Doc tree & documents
export const getTree = (kbId: string) => api.get<DocNode[]>(`/kb/${kbId}/tree`)
export const createNode = (kbId: string, data: { parent_id?: string; title: string; kind: string }) =>
  api.post<DocNode>(`/kb/${kbId}/nodes`, data)
export const getDocument = (kbId: string, nodeId: string) =>
  api.get<Document>(`/kb/${kbId}/nodes/${nodeId}/content`)
export const saveDocument = (kbId: string, nodeId: string, data: { content: string; content_format: string }) =>
  api.put<Document>(`/kb/${kbId}/nodes/${nodeId}/content`, data)
export const deleteNode = (kbId: string, nodeId: string) =>
  api.delete(`/kb/${kbId}/nodes/${nodeId}`)
