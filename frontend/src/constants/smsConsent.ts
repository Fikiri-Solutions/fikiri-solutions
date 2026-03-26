/**
 * Single source of truth for SMS opt-in copy (CTIA/TCPA/Twilio toll-free verification).
 * Used at point of collection (Signup, Account Settings) and documented at /sms-opt-in.
 * Language must: explicitly mention "text messages"/"SMS", state message types,
 * include STOP/HELP/rates, state consent not required for purchase; checkbox unchecked by default.
 */

export const SMS_CONSENT = {
  /** Upfront disclosure shown above the phone field and consent checkbox. Describes what we request consent for (SMS/text). */
  upfrontDisclosure:
    'By entering your mobile number and checking the box below, you consent to receive SMS text messages from Fikiri Solutions LLC. You will receive: verification codes, login and security alerts, and account notifications only. No marketing. Reply STOP to unsubscribe, HELP for help. Message and data rates may apply. Consent is not required to use our services.',

  /** Shorter disclosure for tight UI (e.g. Account Settings). */
  upfrontDisclosureShort:
    'I agree to receive SMS text messages from Fikiri Solutions LLC for verification codes, security alerts, and account notifications. Reply STOP to unsubscribe, HELP for help. Msg & data rates may apply. Consent not required for purchase.',

  /** Exact checkbox label — explicit consent for SMS/text (Error 30513). Lead with "I agree to receive text messages from [Business Name]". */
  checkboxLabel:
    'I agree to receive SMS text messages from Fikiri Solutions LLC for verification codes, login and security alerts, and account notifications. Message and data rates may apply. Reply STOP to unsubscribe, HELP for help. Consent is not required to use our services.',

  /** Section heading for optional SMS block. */
  sectionTitle: 'SMS notifications (optional)',

  /** Opt-in confirmation SMS (sent when user opts in; match toll-free verification submission). */
  optInConfirmationMessage:
    'Fikiri Solutions: You have successfully opted in to receive account and security notifications. Reply STOP to opt out. Reply HELP for help. Msg & data rates may apply.',

  /** HELP reply SMS (match toll-free verification submission). */
  helpMessage:
    'Fikiri Solutions: For help, contact info@fikirisolutions.com or visit https://fikirisolutions.com. Reply STOP to opt out.',

  /** URLs submitted for toll-free verification. */
  privacyPolicyUrl: 'https://fikirisolutions.com/privacy',
  termsUrl: 'https://fikirisolutions.com/terms',
} as const;
