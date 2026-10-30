import { create } from 'zustand'
import type { User } from '../api/types'

interface AuthState {
  user: User | null
  setUser: (u: User | null) => void
  isAuthed: () => boolean
  logout: () => void
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  setUser: (u) => set({ user: u }),
  isAuthed: () => !!localStorage.getItem('access_token'),
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null })
  },
}))
