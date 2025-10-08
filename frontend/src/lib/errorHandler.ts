/**
 * Format API error for display
 * Handles both Pydantic validation errors (422) and string error messages
 */
export function formatApiError(err: any, fallbackMessage = 'An error occurred. Please try again.'): string {
  // Handle 422 validation errors from Pydantic
  if (err.status === 422 && Array.isArray(err.detail)) {
    const firstError = err.detail[0]
    return firstError?.msg || 'Invalid input. Please check your data.'
  }

  // Handle string detail
  if (typeof err.detail === 'string') {
    return err.detail
  }

  // Fallback
  return fallbackMessage
}
