import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient, ApiError } from '../api'
import { authApi } from '../authApi'
import { useAuthStore } from '../../stores/authStore'

const INITIAL_AUTH_STATE = {
  accessToken: 'expired-access-token',
  refreshToken: 'valid-refresh-token',
  user: null,
}

describe('ApiClient token refresh handling', () => {
  beforeEach(() => {
    useAuthStore.setState(INITIAL_AUTH_STATE)
    localStorage.setItem('auth-storage', JSON.stringify({ state: INITIAL_AUTH_STATE }))
  })

  afterEach(() => {
    useAuthStore.setState({ accessToken: null, refreshToken: null, user: null })
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('refreshes tokens and retries once after a 401 response', async () => {
    const refreshedTokens = {
      accessToken: 'new-access-token',
      refreshToken: 'new-refresh-token',
      expiresIn: 3600,
    }

    const refreshSpy = vi
      .spyOn(authApi, 'refresh')
      .mockResolvedValue(refreshedTokens)

    const successfulResponse = new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })

    const fetchMock = vi
      .spyOn(global, 'fetch')
      .mockResolvedValueOnce(new Response('Unauthorized', { status: 401 }))
      .mockResolvedValueOnce(successfulResponse)

    const result = await apiClient.get<{ ok: boolean }>('/v1/subscription/me')

    expect(result).toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(refreshSpy).toHaveBeenCalledWith('valid-refresh-token')

    const secondCallHeaders = fetchMock.mock.calls[1][1]?.headers as Record<string, string>
    expect(secondCallHeaders.Authorization).toBe('Bearer new-access-token')

    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('new-access-token')
    expect(state.refreshToken).toBe('new-refresh-token')
  })

  it('clears auth state when refresh fails after a 401 response', async () => {
    const refreshSpy = vi
      .spyOn(authApi, 'refresh')
      .mockRejectedValue(new Error('refresh failed'))

    vi.spyOn(global, 'fetch').mockResolvedValue(new Response('Unauthorized', { status: 401 }))

    await expect(apiClient.get('/v1/subscription/me')).rejects.toBeInstanceOf(ApiError)

    expect(refreshSpy).toHaveBeenCalledWith('valid-refresh-token')

    const state = useAuthStore.getState()
    expect(state.accessToken).toBeNull()
    expect(state.refreshToken).toBeNull()
    expect(state.user).toBeNull()
  })
})
