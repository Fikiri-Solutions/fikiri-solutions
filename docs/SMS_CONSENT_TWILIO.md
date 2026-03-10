# SMS consent and Twilio (CTIA/TCPA) compliance

To pass Twilio use case 30446, Fikiri collects **express SMS consent** with the required disclosure and optional checkbox.

## Where consent is collected

1. **Signup** (`frontend/src/pages/Signup.tsx`)  
   - Optional **Phone number** field.  
   - Optional **SMS consent** checkbox (unchecked by default) with full disclosure.  
   - Consent is not required to create an account.

2. **Account Management → Profile** (`frontend/src/components/AccountManagement.tsx`)  
   - **Phone number** field.  
   - **SMS consent** checkbox (unchecked by default), directly under the phone field, with disclosure.  
   - Stored in user profile (metadata: `phone`, `sms_consent`, `sms_consent_at`).  
   - SMS notification toggles in the Notifications tab are only effective when the user has consented in Profile.

## Disclosure text (used in both places)

- Clearly mentions **SMS/text messages**.
- States message type: **account and security-related**.
- Includes **STOP** and **HELP**.
- Includes **Msg & data rates may apply**.
- Includes **Consent is not a condition of purchase**.
- Checkbox is **unchecked by default** and **optional**.

Exact copy:

> I agree to receive account and security-related SMS messages from Fikiri Solutions. Reply STOP to opt out. Reply HELP for help. Msg & data rates may apply. Consent is not a condition of purchase.

## Proof for Twilio submission

1. **Screenshot**  
   Capture a single screen that shows:
   - Phone number field  
   - SMS consent checkbox  
   - Full disclosure text  

   Host the image at:

   **https://fikirisolutions.com/images/sms-optin-proof.png**

2. **In Twilio form**  
   - **Proof of consent collected:** paste that exact image URL.  
   - **Opt-In Type:** WEB FORM.  
   - **Use Case:** Transactional only (account/security).  
   - **Sample Message:** must include STOP, HELP, and “Msg & data rates may apply”.  
   - **Opt-In Confirmation Message:** e.g.  
     `Fikiri Solutions: You are subscribed to account notifications. Reply STOP to opt out. Reply HELP for help. Msg & data rates may apply.`  
   - **Help Message Sample:** e.g.  
     `Fikiri Solutions: For help, contact support@fikirisolutions.com or visit https://fikirisolutions.com. Reply STOP to opt out.`  
   - **Additional Info:** state that checkbox consent is required before SMS is enabled and is collected on the same screen as the phone field.

## Backend storage

- **Table:** `users`  
- **Column:** `metadata` (JSON)  
- **Fields:** `phone`, `sms_consent` (boolean), `sms_consent_at` (ISO timestamp when consent was given).  
- **API:** `GET /api/user/profile` returns `phone`, `sms_consent`, `sms_consent_at`.  
  `PUT /api/user/profile` accepts `phone`, `sms_consent` and persists them in `metadata`.

Sending logic (Twilio, workflows) should only send SMS when `metadata.sms_consent` is true and `metadata.phone` is present.
