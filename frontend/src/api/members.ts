import api from './client'
import type { User } from './types'

export interface SpaceMember {
  id: string
  role: string
  user: User
}

export const listMembers = (spaceId: string) => api.get<SpaceMember[]>(`/spaces/${spaceId}/members`)

export const addMember = (spaceId: string, data: { email: string; role: string }) =>
  api.post<SpaceMember>(`/spaces/${spaceId}/members`, data)

export const updateMember = (spaceId: string, memberId: string, data: { role: string }) =>
  api.patch<SpaceMember>(`/spaces/${spaceId}/members/${memberId}`, data)

export const removeMember = (spaceId: string, memberId: string) =>
  api.delete(`/spaces/${spaceId}/members/${memberId}`)
