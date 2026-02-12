/**
 * Simple Error Message Mapper
 * Converts technical errors to plain language with actionable fixes
 */

export interface FriendlyError {
  title: string
  message: string
  steps?: string[]
  type: 'error' | 'warning' | 'info'
}

const errorMap: Record<string, FriendlyError> = {
  // Network errors
  'NETWORK_ERROR': {
    title: 'Connection Problem',
    message: 'Unable to reach our servers.',
    steps: [
      'Check your internet connection',
      'Try refreshing the page',
      'If the problem continues, wait a few minutes and try again'
    ],
    type: 'error'
  },
  'ERR_CONNECTION_REFUSED': {
    title: 'Server Not Available',
    message: 'The server is not responding.',
    steps: [
      'The backend server may not be running',
      'Wait a moment and try again',
      'Contact support if this continues'
    ],
    type: 'warning'
  },

  // Authentication errors
  '401': {
    title: 'Please Sign In',
    message: 'You need to sign in to access this.',
    steps: [
      'Click "Sign In" in the top right',
      'Enter your email and password',
      'If you forgot your password, use "Forgot Password"'
    ],
    type: 'warning'
  },
  '403': {
    title: 'Access Denied',
    message: 'You don\'t have permission for this action.',
    steps: [
      'Make sure you\'re signed in with the correct account',
      'Contact your administrator if you need access'
    ],
    type: 'error'
  },
  '429': {
    title: 'Too Many Requests',
    message: 'You\'ve made too many requests. Please wait a moment.',
    steps: [
      'Wait 30 seconds',
      'Try again',
      'If this continues, you may need to wait longer'
    ],
    type: 'warning'
  },

  // OAuth errors
  'OAUTH_REQUIRED': {
    title: 'Email Connection Required',
    message: 'You need to connect your email account first.',
    steps: [
      'Go to Integrations page',
      'Click "Connect Gmail" or "Connect Outlook"',
      'Follow the sign-in steps'
    ],
    type: 'info'
  },
  'OAUTH_ERROR': {
    title: 'Email Connection Failed',
    message: 'We couldn\'t connect your email account.',
    steps: [
      'Make sure you completed the sign-in process',
      'Try disconnecting and reconnecting',
      'Check that you granted all required permissions'
    ],
    type: 'error'
  },
  'redirect_uri_mismatch': {
    title: 'Connection Setup Issue',
    message: 'There\'s a configuration problem with email connection.',
    steps: [
      'This is usually a temporary issue',
      'Try again in a few minutes',
      'Contact support if it continues'
    ],
    type: 'warning'
  },

  // API errors
  '500': {
    title: 'Server Error',
    message: 'Something went wrong on our end.',
    steps: [
      'Try again in a moment',
      'If the problem continues, contact support',
      'Your data is safe - nothing was lost'
    ],
    type: 'error'
  },
  '503': {
    title: 'Service Unavailable',
    message: 'This feature is temporarily unavailable.',
    steps: [
      'We\'re working on it',
      'Try again in a few minutes',
      'Check our status page for updates'
    ],
    type: 'warning'
  },

  // Validation errors
  'MISSING_REQUIRED_FIELDS': {
    title: 'Missing Information',
    message: 'Please fill in all required fields.',
    steps: [
      'Check the form for highlighted fields',
      'Fill in any empty required fields',
      'Try submitting again'
    ],
    type: 'warning'
  },
  'INVALID_EMAIL': {
    title: 'Invalid Email',
    message: 'Please enter a valid email address.',
    steps: [
      'Check for typos in your email',
      'Make sure it includes @ and a domain',
      'Example: name@example.com'
    ],
    type: 'warning'
  },
  'WEAK_PASSWORD': {
    title: 'Password Too Weak',
    message: 'Your password needs to be stronger.',
    steps: [
      'Use at least 8 characters',
      'Include uppercase and lowercase letters',
      'Add numbers and special characters'
    ],
    type: 'warning'
  },

  // Gmail/Outlook specific
  'GMAIL_SYNC_ERROR': {
    title: 'Email Sync Failed',
    message: 'We couldn\'t sync your emails right now.',
    steps: [
      'Check that Gmail is still connected',
      'Try syncing again',
      'If it continues, disconnect and reconnect Gmail'
    ],
    type: 'error'
  },
  'OUTLOOK_SYNC_ERROR': {
    title: 'Email Sync Failed',
    message: 'We couldn\'t sync your Outlook emails right now.',
    steps: [
      'Check that Outlook is still connected',
      'Try syncing again',
      'If it continues, disconnect and reconnect Outlook'
    ],
    type: 'error'
  },
  'TOKEN_EXPIRED': {
    title: 'Connection Expired',
    message: 'Your email connection needs to be refreshed.',
    steps: [
      'Go to Integrations page',
      'Click "Reconnect" on your email account',
      'Sign in again to refresh the connection'
    ],
    type: 'warning'
  },

  // AI errors
  'OPENAI_ERROR': {
    title: 'AI Service Unavailable',
    message: 'The AI assistant is temporarily unavailable.',
    steps: [
      'Try again in a moment',
      'Check that your API key is configured',
      'Contact support if this continues'
    ],
    type: 'warning'
  },
  'AI_RATE_LIMIT': {
    title: 'AI Usage Limit',
    message: 'You\'ve reached the AI usage limit for now.',
    steps: [
      'Wait a few minutes',
      'Try again later',
      'Consider upgrading your plan for higher limits'
    ],
    type: 'info'
  },

  // CRM errors
  'LEAD_NOT_FOUND': {
    title: 'Lead Not Found',
    message: 'The lead you\'re looking for doesn\'t exist.',
    steps: [
      'Check that you have the correct lead ID',
      'The lead may have been deleted',
      'Try refreshing the CRM page'
    ],
    type: 'warning'
  },
  'DUPLICATE_LEAD': {
    title: 'Duplicate Lead',
    message: 'A lead with this email already exists.',
    steps: [
      'Check your CRM for existing leads',
      'Update the existing lead instead',
      'Or use a different email address'
    ],
    type: 'info'
  }
}

/**
 * Convert any error to a friendly message
 */
export function getFriendlyError(error: any): FriendlyError {
  // Check for specific error codes first
  if (error?.error_code && errorMap[error.error_code]) {
    return errorMap[error.error_code]
  }

  // Check status codes
  const status = error?.status || error?.response?.status
  if (status && errorMap[String(status)]) {
    return errorMap[String(status)]
  }

  // Check error messages for keywords
  const message = error?.message || error?.error || String(error || '')
  const messageLower = message.toLowerCase()

  // Network errors
  if (messageLower.includes('network') || messageLower.includes('fetch') || messageLower.includes('connection refused')) {
    return errorMap['NETWORK_ERROR']
  }

  // OAuth errors
  if (messageLower.includes('oauth') || messageLower.includes('redirect_uri')) {
    if (messageLower.includes('redirect_uri')) {
      return errorMap['redirect_uri_mismatch']
    }
    return errorMap['OAUTH_ERROR']
  }

  // Email sync errors
  if (messageLower.includes('gmail sync') || messageLower.includes('gmail_sync')) {
    return errorMap['GMAIL_SYNC_ERROR']
  }
  if (messageLower.includes('outlook sync') || messageLower.includes('outlook_sync')) {
    return errorMap['OUTLOOK_SYNC_ERROR']
  }

  // Token errors
  if (messageLower.includes('token') && (messageLower.includes('expired') || messageLower.includes('invalid'))) {
    return errorMap['TOKEN_EXPIRED']
  }

  // AI errors
  if (messageLower.includes('openai') || messageLower.includes('api key')) {
    return errorMap['OPENAI_ERROR']
  }

  // Validation errors
  if (messageLower.includes('required') || messageLower.includes('missing')) {
    return errorMap['MISSING_REQUIRED_FIELDS']
  }
  if (messageLower.includes('email') && (messageLower.includes('invalid') || messageLower.includes('format'))) {
    return errorMap['INVALID_EMAIL']
  }
  if (messageLower.includes('password') && messageLower.includes('weak')) {
    return errorMap['WEAK_PASSWORD']
  }

  // Default fallback
  return {
    title: 'Something Went Wrong',
    message: 'An unexpected error occurred. We\'ve been notified and are looking into it.',
    steps: [
      'Try refreshing the page',
      'If the problem continues, contact support',
      'Your data is safe'
    ],
    type: 'error'
  }
}

