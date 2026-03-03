/**
 * Single source of truth for SMS opt-in copy (CTIA/TCPA/Twilio toll-free verification).
 * Used at point of collection (Signup, Account Settings) and documented at /sms-opt-in.
 * Language must: explicitly mention "text messages"/"SMS", state message types,
 * include STOP/HELP/rates, state consent not required for purchase; checkbox unchecked by default.
 */

export const SMS_CONSENT = {
  /** Upfront disclosure shown above the phone field and consent checkbox. */
  upfrontDisclosure:
    'By providing your mobile number and checking the box below, you expressly consent to receive automated text messages (SMS) from Fikiri Solutions LLC at the number you provide. Messages are limited to: (1) account verification codes, (2) login and security alerts, and (3) account status notifications. We do not send marketing or promotional text messages. Message frequency varies as needed. You can reply STOP at any time to opt out or HELP for help. Message and data rates may apply. Consent is not required to use our services or make a purchase.',

  /** Shorter disclosure for tight UI (e.g. Account Settings). */
  upfrontDisclosureShort:
    'Fikiri Solutions LLC may send you text messages (SMS) for verification codes, login and security alerts, and account notifications only. No marketing. Reply STOP to opt out, HELP for help. Msg & data rates may apply. Consent is not required for purchase.',

  /** Exact checkbox label — must explicitly request consent for SMS/text messages (Error 30513). */
  checkboxLabel:
    'I agree to receive text messages (SMS) from Fikiri Solutions LLC for account verification codes, login and security alerts, and account notifications. Reply STOP to opt out. Reply HELP for help. Msg & data rates may apply. Consent is not a condition of purchase.',

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
