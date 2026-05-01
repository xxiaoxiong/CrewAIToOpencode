import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface User {
  id: string
  email: string
  name: string
  role: 'customer' | 'admin'
}

interface AuthStore {
  user: User | null
  login: (email: string, password: string) => boolean
  logout: () => void
  register: (email: string, password: string, name: string) => boolean
}

const MOCK_USERS: Record<string, { password: string; user: User }> = {
  'admin@shop.com': {
    password: 'admin123',
    user: { id: '1', email: 'admin@shop.com', name: 'Admin User', role: 'admin' },
  },
  'user@shop.com': {
    password: 'user123',
    user: { id: '2', email: 'user@shop.com', name: 'Test User', role: 'customer' },
  },
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,

      login: (email: string, password: string) => {
        const mockUser = MOCK_USERS[email]
        if (mockUser && mockUser.password === password) {
          set({ user: mockUser.user })
          return true
        }
        return false
      },

      logout: () => set({ user: null }),

      register: (email: string, password: string, name: string) => {
        if (MOCK_USERS[email]) return false
        const newUser: User = {
          id: Date.now().toString(),
          email,
          name,
          role: 'customer',
        }
        MOCK_USERS[email] = { password, user: newUser }
        set({ user: newUser })
        return true
      },
    }),
    {
      name: 'auth-storage',
    }
  )
)