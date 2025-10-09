import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  status: string
  mfaEnabled: boolean
  emailVerified: boolean
  roles: string[]
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  setTokens: (access: string, refresh: string) => void
  setUser: (user: User) => void
  clearAuth: () => void
  isAuthenticated: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,

      setTokens: (access: string, refresh: string) => {
        set({ accessToken: access, refreshToken: refresh })
      },

      setUser: (user: User) => {
        set({ user })
      },

      clearAuth: () => {
        set({ accessToken: null, refreshToken: null, user: null })
      },

      isAuthenticated: () => {
        return !!get().accessToken && !!get().refreshToken
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
    },
  ),
)
