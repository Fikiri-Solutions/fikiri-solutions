/**
 * Centralized `autocomplete` values (WHATWG HTML).
 *
 * - `section-*` scopes a set of fields so “create account” data is not mixed with
 *   “sign in”, “contact us”, or “reset password” datasets in the same profile.
 * - Login uses `username` + `current-password` so password managers reliably
 *   match the credential pair (email-as-username is still `username`).
 *
 * @see https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#autofill-detail-tokens
 */
export const AUTOCOMPLETE = {
  /** Existing account: identifier + current password */
  login: {
    identifier: 'section-fikiri-login username',
    password: 'section-fikiri-login current-password',
  },

  /** New account: profile + new password (confirm uses same token as primary) */
  signup: {
    givenName: 'section-fikiri-signup given-name',
    familyName: 'section-fikiri-signup family-name',
    email: 'section-fikiri-signup email',
    organization: 'section-fikiri-signup organization',
    tel: 'section-fikiri-signup tel',
    newPassword: 'section-fikiri-signup new-password',
    newPasswordConfirm: 'section-fikiri-signup new-password',
  },

  /** Marketing / support contact — separate from auth */
  contact: {
    name: 'section-fikiri-contact name',
    email: 'section-fikiri-contact email',
    tel: 'section-fikiri-contact tel',
    organization: 'section-fikiri-contact organization',
    /** No standard token for free-text subject */
    subject: 'off',
    message: 'off',
  },

  /** One field: account email for recovery link */
  forgotPassword: {
    email: 'section-fikiri-recovery email',
  },

  /** Logged-out password change (same token on both fields is valid) */
  resetPassword: {
    newPassword: 'section-fikiri-reset new-password',
    newPasswordConfirm: 'section-fikiri-reset new-password',
  },

  /** Pre-signup onboarding (name + org) */
  onboarding: {
    name: 'section-fikiri-onboarding name',
    organization: 'section-fikiri-onboarding organization',
    industry: 'off',
  },

  /** Not part of autofill profiles */
  off: 'off',
} as const
