import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getToken, setToken, getUser, setUser, isAuthenticated, logout } from '../../../src/utils/auth'

describe('Auth Utils', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('getToken', () => {
    it('returns stored token from localStorage', () => {
      localStorage.setItem('analytics_access_token', 'test-token-123')

      const token = getToken()

      expect(token).toBe('test-token-123')
    })

    it('returns null when no token stored', () => {
      const token = getToken()

      expect(token).toBeNull()
    })
  })

  describe('setToken', () => {
    it('stores token in localStorage', () => {
      setToken('new-token-456')

      expect(localStorage.getItem('analytics_access_token')).toBe('new-token-456')
    })
  })

  describe('getUser', () => {
    it('returns parsed user from localStorage', () => {
      const user = { email: 'test@example.com', name: 'Test User' }
      localStorage.setItem('analytics_user', JSON.stringify(user))

      const result = getUser()

      expect(result).toEqual(user)
    })

    it('returns null when no user stored', () => {
      const result = getUser()

      expect(result).toBeNull()
    })

    it('returns null for invalid JSON', () => {
      localStorage.setItem('analytics_user', 'invalid-json')

      const result = getUser()

      expect(result).toBeNull()
    })
  })

  describe('setUser', () => {
    it('stores user in localStorage as JSON', () => {
      const user = { email: 'test@example.com', name: 'Test User' }

      setUser(user)

      expect(localStorage.getItem('analytics_user')).toBe(JSON.stringify(user))
    })
  })

  describe('isAuthenticated', () => {
    it('returns true when token is valid and not expired', () => {
      // Create a valid JWT with future expiration
      const payload = {
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour from now
      }
      const token = `header.${btoa(JSON.stringify(payload))}.signature`
      localStorage.setItem('analytics_access_token', token)

      const result = isAuthenticated()

      expect(result).toBe(true)
    })

    it('returns false when no token', () => {
      const result = isAuthenticated()

      expect(result).toBe(false)
    })

    it('returns false for expired token', () => {
      // Create an expired JWT
      const payload = {
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) - 3600, // 1 hour ago
      }
      const token = `header.${btoa(JSON.stringify(payload))}.signature`
      localStorage.setItem('analytics_access_token', token)

      const result = isAuthenticated()

      expect(result).toBe(false)
    })

    it('returns false for invalid token format', () => {
      localStorage.setItem('analytics_access_token', 'invalid-token')

      const result = isAuthenticated()

      expect(result).toBe(false)
    })
  })

  describe('logout', () => {
    it('removes token and user from localStorage', () => {
      localStorage.setItem('analytics_access_token', 'some-token')
      localStorage.setItem('analytics_user', '{"email":"test@example.com"}')

      logout()

      expect(localStorage.getItem('analytics_access_token')).toBeNull()
      expect(localStorage.getItem('analytics_user')).toBeNull()
    })
  })
})
