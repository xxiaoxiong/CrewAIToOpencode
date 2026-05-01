import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore } from '@/context/AuthStore'

describe('Auth Store', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
  })

  it('should login with valid credentials (admin)', () => {
    const { login, user } = useAuthStore.getState()
    const success = login('admin@shop.com', 'admin123')
    expect(success).toBe(true)
    const currentUser = useAuthStore.getState().user
    expect(currentUser?.role).toBe('admin')
    expect(currentUser?.email).toBe('admin@shop.com')
  })

  it('should login with valid credentials (customer)', () => {
    const { login } = useAuthStore.getState()
    const success = login('user@shop.com', 'user123')
    expect(success).toBe(true)
    const currentUser = useAuthStore.getState().user
    expect(currentUser?.role).toBe('customer')
  })

  it('should fail login with invalid credentials', () => {
    const { login, user } = useAuthStore.getState()
    const success = login('invalid@shop.com', 'wrongpass')
    expect(success).toBe(false)
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('should logout and clear user', () => {
    const { login, logout } = useAuthStore.getState()
    login('admin@shop.com', 'admin123')
    expect(useAuthStore.getState().user).toBeDefined()
    logout()
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('should register new user', () => {
    const { register, user } = useAuthStore.getState()
    const success = register('newuser@test.com', 'password123', 'New User')
    expect(success).toBe(true)
    const currentUser = useAuthStore.getState().user
    expect(currentUser?.email).toBe('newuser@test.com')
    expect(currentUser?.name).toBe('New User')
    expect(currentUser?.role).toBe('customer')
  })

  it('should not register duplicate email', () => {
    const { register } = useAuthStore.getState()
    register('admin@shop.com', 'password123', 'Duplicate')
    const currentUser = useAuthStore.getState().user
    expect(currentUser?.email).not.toBe('admin@shop.com')
  })
})