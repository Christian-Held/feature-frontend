// Error messages per spec (Section 17)
export const ERROR_MESSAGES = {
  REGISTRATION_SUCCESS: "Registration almost done — check your email. The link is valid for 24 hours.",
  UNVERIFIED: "You must confirm your registration first. We've sent you an email.",
  INVALID_OTP: "Invalid security code.",
  CAPTCHA_REQUIRED: "Captcha required.",
  UNAUTHORIZED: "You don't have permission to perform this action.",
  CAP_REACHED: "Your monthly spending limit has been reached. Adjust your limit to continue.",
  WRONG_CREDENTIALS: "Email or password is incorrect.",
} as const

// Turnstile configuration
export const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || '1x00000000000000000000AA'
