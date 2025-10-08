export interface RegisterRequest {
  email: string
  password: string
  captchaToken: string
}

export interface RegisterResponse {
  message: string
}

export interface LoginRequest {
  email: string
  password: string
  captchaToken?: string
}

export interface LoginResponse {
  requires2fa: boolean
  challengeId?: string
  accessToken?: string
  refreshToken?: string
  expiresIn?: number
}

export interface TwoFAVerifyRequest {
  challengeId: string
  otp: string
  captchaToken?: string
}

export interface TwoFAVerifyResponse {
  accessToken: string
  refreshToken: string
  expiresIn: number
}

export interface RefreshResponse {
  accessToken: string
  refreshToken: string
  expiresIn: number
}

export interface TwoFAEnableInitResponse {
  secret: string
  otpauthUrl: string
  qrSvg: string
  challengeId: string
}

export interface TwoFAEnableCompleteResponse {
  recoveryCodes: string[]
}

export interface UserResponse {
  id: string
  email: string
  status: string
  mfaEnabled: boolean
  emailVerified: boolean
  roles: string[]
}

export interface RecoveryLoginRequest {
  email: string
  recoveryCode: string
  password?: string
  challengeId?: string
}

export const authApi = {
  // Registration & Verification
  register: async (data: RegisterRequest): Promise<RegisterResponse> => {
    const response = await fetch('/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Registration failed' }
    }
    return response.json()
  },

  resendVerification: async (email: string): Promise<{ message: string }> => {
    const response = await fetch('/v1/auth/resend-verification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Failed to resend verification' }
    }
    return response.json()
  },

  verifyEmail: async (token: string): Promise<{ message: string }> => {
    const response = await fetch(`/v1/auth/verify-email?token=${token}`, {
      method: 'GET',
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Verification failed' }
    }
    return response.json()
  },

  // Login & Session
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await fetch('/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Login failed' }
    }
    return response.json()
  },

  verify2FA: async (data: TwoFAVerifyRequest): Promise<TwoFAVerifyResponse> => {
    const response = await fetch('/v1/auth/2fa/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || '2FA verification failed' }
    }
    return response.json()
  },

  logout: async (refreshToken: string): Promise<{ message: string }> => {
    const response = await fetch('/v1/auth/logout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken }),
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Logout failed' }
    }
    return response.json()
  },

  refresh: async (refreshToken: string): Promise<RefreshResponse> => {
    const response = await fetch('/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken }),
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Token refresh failed' }
    }
    return response.json()
  },

  me: async (accessToken: string): Promise<UserResponse> => {
    const response = await fetch('/v1/auth/me', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Failed to get user info' }
    }
    return response.json()
  },

  // Password Reset
  forgotPassword: async (email: string): Promise<{ message: string }> => {
    const response = await fetch('/v1/auth/forgot-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Failed to send reset email' }
    }
    return response.json()
  },

  resetPassword: async (token: string, newPassword: string): Promise<{ message: string }> => {
    const response = await fetch('/v1/auth/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, password: newPassword }),
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Password reset failed' }
    }
    return response.json()
  },

  // 2FA Management
  enable2FAInit: async (accessToken: string): Promise<TwoFAEnableInitResponse> => {
    const response = await fetch('/v1/auth/2fa/enable-init', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Failed to initialize 2FA' }
    }
    return response.json()
  },

  enable2FAComplete: async (accessToken: string, challengeId: string, otp: string): Promise<TwoFAEnableCompleteResponse> => {
    const response = await fetch('/v1/auth/2fa/enable-complete', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ challengeId, otp }),
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Failed to enable 2FA' }
    }
    return response.json()
  },

  disable2FA: async (accessToken: string, password: string, otp: string): Promise<{ message: string }> => {
    const response = await fetch('/v1/auth/2fa/disable', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ password, otp }),
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Failed to disable 2FA' }
    }
    return response.json()
  },

  // Recovery Login
  recoveryLogin: async (data: RecoveryLoginRequest): Promise<TwoFAVerifyResponse> => {
    const response = await fetch('/v1/auth/recovery-login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) {
      const error = await response.json()
      throw { status: response.status, detail: error.detail || 'Recovery login failed' }
    }
    return response.json()
  },
}
