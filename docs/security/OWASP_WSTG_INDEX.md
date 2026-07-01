# OWASP WSTG — Fikiri Local Reference Index

Planning artifact for **focused security audits**. Does not replace live OWASP content.

## Agent quick start

1. Read this file for scope and Fikiri mapping tags.
2. Open **section overview** markdown under `docs/security/owasp-wstg/` (status `ok`) for child-test links.
3. For leaf tests, prefer live OWASP URLs when local file status is `stub` (see below).
4. Machine-readable paths: `docs/security/owasp-wstg/manifest.json`.
5. Do **not** load all 158 files — pick one audit theme from [Suggested audit order](#suggested-audit-order).

## Mirror status

| Metric | Value |
|--------|-------|
| Scrape output | `docs/security/owasp-wstg/` |
| Pages saved | 158 |
| Section overviews with content | 21 |
| Leaf pages with full body locally | ~0 (137 stubs return OWASP 404 HTML) |
| Scraper | `scripts/scrape_owasp_wstg.py` |

**Caveat:** Most leaf URLs were fetched with a trailing-slash mismatch; stubs contain OWASP 404 pages. Section overviews (e.g. `4-Web_Application_Security_Testing/01-Information_Gathering.md`) list correct live URLs. Re-scrape leaf pages without trailing slash before offline-only audits.

## Suggested audit order

| # | Theme | WSTG refs | Local overview | Future Fikiri probe (not audited here) |
|---|-------|-----------|----------------|--------------------------------------|
| 1 | Information leakage & deployment exposure | 4.1, 4.2 | `owasp-wstg/4-Web_Application_Security_Testing/01-Information_Gathering.md, 02-Configuration_and_Deployment_Management_Testing.md` | frontend/dist, Vercel headers, robots/meta, backups, source maps |
| 2 | Authorization / IDOR / tenant isolation | 4.5, 4.12.2 | `owasp-wstg/4-Web_Application_Security_Testing/05-Authorization_Testing.md, 12-API_Testing.md` | CRM leads, API object access, `user_id` scoping |
| 3 | Authentication & session / JWT | 4.4, 4.6 | `owasp-wstg/4-Web_Application_Security_Testing/04-Authentication_Testing.md, 06-Session_Management_Testing.md` | auth routes, JWT, cookies, logout, MFA |
| 4 | API excessive data exposure | 4.12 | `owasp-wstg/4-Web_Application_Security_Testing/12-API_Testing.md` | list endpoints, serializers, pagination |
| 5 | OAuth / Gmail integration | 4.5.5.x | `owasp-wstg/4-Web_Application_Security_Testing/05-Authorization_Testing.md` | core/app_oauth.py, Gmail callbacks, state/CSRF |
| 6 | Stripe / payment workflows | 4.10.10 | `owasp-wstg/4-Web_Application_Security_Testing/10-Business_Logic_Testing.md` | billing routes, webhooks, signature verify |
| 7 | Browser storage & PWA / service worker | 4.11.12, 4.2 | `owasp-wstg/4-Web_Application_Security_Testing/11-Client-side_Testing.md` | localStorage tokens, sw.js cache, offline assets |
| 8 | File upload handling | 4.10.8–4.10.9, 4.2.3 | `owasp-wstg/4-Web_Application_Security_Testing/10-Business_Logic_Testing.md` | CRM CSV import, attachments |
| 9 | Error handling / logging leakage | 4.8 | `owasp-wstg/4-Web_Application_Security_Testing/08-Testing_for_Error_Handling.md` | API error bodies, stack traces in responses |
| 10 | CORS / security headers | 4.2.7–4.2.14 | `owasp-wstg/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing.md` | core/security.py, Vercel CDN headers |

## Fikiri thematic map

| Tag | Use when auditing | Primary WSTG areas | Local overview |
|-----|-------------------|--------------------|----------------|
| `frontend-leakage` | Source maps, JS secrets, HTML comments | 4.1.5, 4.11 | `owasp-wstg/4-Web_Application_Security_Testing/01-Information_Gathering.md, 11-Client-side_Testing.md` |
| `route-inventory` | Hidden routes, admin URLs, attack surface | 4.1.4–4.1.6, 4.2.5 | `owasp-wstg/4-Web_Application_Security_Testing/01-Information_Gathering.md, 02-Configuration...md` |
| `admin-rbac` | Admin interfaces and role definitions | 4.2.5, 4.3.1, 4.12.4 | `owasp-wstg/4-Web_Application_Security_Testing/02-Configuration...md, 03-Identity...md, 12-API_Testing.md` |
| `tenant-isolation` | IDOR, BOLA, cross-tenant reads/writes | 4.5.4, 4.12.2 | `owasp-wstg/4-Web_Application_Security_Testing/05-Authorization_Testing.md, 12-API_Testing.md` |
| `oauth-gmail` | OAuth state, token storage, redirect URI | 4.5.5 | `owasp-wstg/4-Web_Application_Security_Testing/05-Authorization_Testing.md` |
| `stripe-payments` | Checkout, webhooks, workflow bypass | 4.10.10 | `owasp-wstg/4-Web_Application_Security_Testing/10-Business_Logic_Testing.md` |
| `api-exposure` | Over-fetching, verbose errors in lists | 4.12.3 | `owasp-wstg/4-Web_Application_Security_Testing/12-API_Testing.md` |
| `browser-storage` | JWT/localStorage, session fixation via XSS | 4.11.12, 4.6 | `owasp-wstg/4-Web_Application_Security_Testing/11-Client-side_Testing.md, 06-Session...md` |
| `pwa-sw-cache` | Stale auth in SW cache, offline assets | 4.2, 4.11 | `owasp-wstg/4-Web_Application_Security_Testing/02-Configuration...md, 11-Client-side_Testing.md` |
| `file-upload` | CSV/import, malicious types | 4.10.8–4.10.9, 4.2.3 | `owasp-wstg/4-Web_Application_Security_Testing/10-Business_Logic_Testing.md` |
| `error-logging` | Stack traces, internal paths in JSON errors | 4.8.1–4.8.2 | `owasp-wstg/4-Web_Application_Security_Testing/08-Testing_for_Error_Handling.md` |
| `cors-headers` | CSP, HSTS, CORS, security headers | 4.2.7–4.2.14, 4.11.7 | `owasp-wstg/4-Web_Application_Security_Testing/02-Configuration...md, 11-Client-side_Testing.md` |
| `session-jwt` | JWT validation, logout, concurrent sessions | 4.6, 4.4 | `owasp-wstg/4-Web_Application_Security_Testing/06-Session_Management_Testing.md, 04-Authentication_Testing.md` |

## Major sections (local paths)

| Section | Local path | Purpose |
|---------|------------|---------|
| 0 | `owasp-wstg/0-Foreword.md` | Scope and goals of WSTG |
| 1 | `owasp-wstg/1-Frontispiece.md` | Credits and document metadata |
| 2 | `owasp-wstg/2-Introduction.md` | Testing principles, SDLC integration |
| 3 | `owasp-wstg/3-The_OWASP_Testing_Framework.md` | Phased testing framework |
| 4 | `owasp-wstg/4-Web_Application_Security_Testing.md` | Main test catalog (4.0–4.12) |
| 5 | `owasp-wstg/5-Reporting.md` | How to report findings |
| 6 | `owasp-wstg/6-Appendix.md` | Tools, fuzzing, DevTools reference |

### Section 4 overviews (use these for child-test links)

- **4.0 Introduction and Objectives** — `owasp-wstg/4-Web_Application_Security_Testing/00-Introduction_and_Objectives.md`
- **4.1 Information Gathering** — `owasp-wstg/4-Web_Application_Security_Testing/01-Information_Gathering.md`
- **4.2 Configuration and Deployment Management Testing** — `owasp-wstg/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing.md`
- **4.3 Identity Management Testing** — `owasp-wstg/4-Web_Application_Security_Testing/03-Identity_Management_Testing.md`
- **4.4 Authentication Testing** — `owasp-wstg/4-Web_Application_Security_Testing/04-Authentication_Testing.md`
- **4.5 Authorization Testing** — `owasp-wstg/4-Web_Application_Security_Testing/05-Authorization_Testing.md`
- **4.6 Session Management Testing** — `owasp-wstg/4-Web_Application_Security_Testing/06-Session_Management_Testing.md`
- **4.7 Input Validation Testing** — `owasp-wstg/4-Web_Application_Security_Testing/07-Input_Validation_Testing.md`
- **4.8 Testing for Error Handling** — `owasp-wstg/4-Web_Application_Security_Testing/08-Testing_for_Error_Handling.md`
- **4.9 Testing for Weak Cryptography** — `owasp-wstg/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography.md`
- **4.10 Business Logic Testing** — `owasp-wstg/4-Web_Application_Security_Testing/10-Business_Logic_Testing.md`
- **4.11 Client-Side Testing** — `owasp-wstg/4-Web_Application_Security_Testing/11-Client-side_Testing.md`
- **4.12 API Testing** — `owasp-wstg/4-Web_Application_Security_Testing/12-API_Testing.md`

## Section 4 test index (compact)

Local path prefix: `owasp-wstg/`. Status: `stub` = 404 placeholder on disk; use live URL from overview link.

### 4.1

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 4.1.1 (WSTG-INFO-01) | Conduct Search Engine Discovery Reconnaissance for I... | `4-Web_Application_Security_Testing/01-Information_Gathering/01-Conduct_Search_Engine_Discovery_Reconnaissance_for_Information_Leakage.md` | info-leakage |
| 4.1.10 (WSTG-INFO-10) | Map Application Architecture | `4-Web_Application_Security_Testing/01-Information_Gathering/10-Map_Application_Architecture.md` | info-leakage |
| 4.1.2 (WSTG-INFO-02) | Fingerprint Web Server | `4-Web_Application_Security_Testing/01-Information_Gathering/02-Fingerprint_Web_Server.md` | info-leakage |
| 4.1.3 (WSTG-INFO-03) | Review Webserver Metafiles for Information Leakage | `4-Web_Application_Security_Testing/01-Information_Gathering/03-Review_Webserver_Metafiles_for_Information_Leakage.md` | info-leakage |
| 4.1.4 (WSTG-INFO-04) | Attack Surface Identification | `4-Web_Application_Security_Testing/01-Information_Gathering/04-Attack_Surface_Identification.md` | route-inventory, admin-rbac |
| 4.1.5 (WSTG-INFO-05) | Review Web Page Content for Information Leakage | `4-Web_Application_Security_Testing/01-Information_Gathering/05-Review_Web_Page_Content_for_Information_Leakage.md` | frontend-leakage, source-maps |
| 4.1.6 (WSTG-INFO-06) | Identify Application Entry Points | `4-Web_Application_Security_Testing/01-Information_Gathering/06-Identify_Application_Entry_Points.md` | info-leakage |
| 4.1.7 (WSTG-INFO-07) | Map Execution Paths Through Application | `4-Web_Application_Security_Testing/01-Information_Gathering/07-Map_Execution_Paths_Through_Application.md` | info-leakage |
| 4.1.8 (WSTG-INFO-08) | Fingerprint Web Application Framework | `4-Web_Application_Security_Testing/01-Information_Gathering/08-Fingerprint_Web_Application_Framework.md` | info-leakage |
| 4.1.9 (WSTG-INFO-09) | Fingerprint Web Application | `4-Web_Application_Security_Testing/01-Information_Gathering/09-Fingerprint_Web_Application.md` | info-leakage |

### 4.2

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 4.2.1 | Test Network Infrastructure Configuration | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/01-Test_Network_Infrastructure_Configuration.md` | cors-headers, deployment-exposure |
| 4.2.10 | Test for Subdomain Takeover | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/10-Test_for_Subdomain_Takeover.md` | cors-headers, deployment-exposure |
| 4.2.11 | Test Cloud Storage | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/11-Test_Cloud_Storage.md` | cors-headers, deployment-exposure |
| 4.2.12 | Test for Content Security Policy | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/12-Test_for_Content_Security_Policy.md` | cors-headers, deployment-exposure |
| 4.2.13 | Test for Path Confusion | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/13-Test_for_Path_Confusion.md` | cors-headers, deployment-exposure |
| 4.2.14 | Test for Other HTTP Security Header Misconfigurations | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/14-Test_Other_HTTP_Security_Header_Misconfigurations.md` | cors-headers, deployment-exposure |
| 4.2.2 | Test Application Platform Configuration | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/02-Test_Application_Platform_Configuration.md` | cors-headers, deployment-exposure |
| 4.2.3 | Test File Extensions Handling for Sensitive Information | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/03-Test_File_Extensions_Handling_for_Sensitive_Information.md` | cors-headers, deployment-exposure |
| 4.2.4 | Review Old Backup and Unreferenced Files for Sensiti... | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/04-Review_Old_Backup_and_Unreferenced_Files_for_Sensitive_Information.md` | info-leakage, cors-headers, deployment-exposure |
| 4.2.5 | Enumerate Infrastructure and Application Admin Inter... | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/05-Enumerate_Infrastructure_and_Application_Admin_Interfaces.md` | admin-rbac, cors-headers, deployment-exposure |
| 4.2.6 | Test HTTP Methods | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/06-Test_HTTP_Methods.md` | cors-headers, deployment-exposure |
| 4.2.7 | Test HTTP Strict Transport Security | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/07-Test_HTTP_Strict_Transport_Security.md` | cors-headers, deployment-exposure |
| 4.2.8 | Test RIA Cross Domain Policy | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/08-Test_RIA_Cross_Domain_Policy.md` | cors-headers, deployment-exposure |
| 4.2.9 | Test File Permission | `4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/09-Test_File_Permission.md` | cors-headers, deployment-exposure |

### 4.3

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 4.3.1 | Test Role Definitions | `4-Web_Application_Security_Testing/03-Identity_Management_Testing/01-Test_Role_Definitions.md` | identity-roles |
| 4.3.2 | Test User Registration Process | `4-Web_Application_Security_Testing/03-Identity_Management_Testing/02-Test_User_Registration_Process.md` | identity-roles |
| 4.3.3 | Test Account Provisioning Process | `4-Web_Application_Security_Testing/03-Identity_Management_Testing/03-Test_Account_Provisioning_Process.md` | identity-roles |
| 4.3.4 | Testing for Account Enumeration and Guessable User A... | `4-Web_Application_Security_Testing/03-Identity_Management_Testing/04-Testing_for_Account_Enumeration_and_Guessable_User_Account.md` | identity-roles |
| 4.3.5 | Testing for Weak or Unenforced Username Policy | `4-Web_Application_Security_Testing/03-Identity_Management_Testing/05-Testing_for_Weak_or_Unenforced_Username_Policy.md` | identity-roles |

### 4.4

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 4.4.1 | Testing for Credentials Transported over an Encrypte... | `4-Web_Application_Security_Testing/04-Authentication_Testing/01-Testing_for_Credentials_Transported_over_an_Encrypted_Channel.md` | auth-session |
| 4.4.10 | Testing for Weaker Authentication in Alternative Cha... | `4-Web_Application_Security_Testing/04-Authentication_Testing/10-Testing_for_Weaker_Authentication_in_Alternative_Channel.md` | auth-session |
| 4.4.11 | Testing Multi-Factor Authentication | `4-Web_Application_Security_Testing/04-Authentication_Testing/11-Testing_Multi-Factor_Authentication.md` | auth-session |
| 4.4.2 | Testing for Default Credentials | `4-Web_Application_Security_Testing/04-Authentication_Testing/02-Testing_for_Default_Credentials.md` | auth-session |
| 4.4.3 | Testing for Weak Lock Out Mechanism | `4-Web_Application_Security_Testing/04-Authentication_Testing/03-Testing_for_Weak_Lock_Out_Mechanism.md` | auth-session |
| 4.4.4 | Testing for Bypassing Authentication Schema | `4-Web_Application_Security_Testing/04-Authentication_Testing/04-Testing_for_Bypassing_Authentication_Schema.md` | auth-session |
| 4.4.5 | Testing for Vulnerable Remember Password | `4-Web_Application_Security_Testing/04-Authentication_Testing/05-Testing_for_Vulnerable_Remember_Password.md` | auth-session |
| 4.4.6 | Testing for Browser Cache Weaknesses | `4-Web_Application_Security_Testing/04-Authentication_Testing/06-Testing_for_Browser_Cache_Weaknesses.md` | auth-session |
| 4.4.7 | Testing for Weak Authentication Methods | `4-Web_Application_Security_Testing/04-Authentication_Testing/07-Testing_for_Weak_Authentication_Methods.md` | auth-session |
| 4.4.8 | Testing for Weak Security Question Answer | `4-Web_Application_Security_Testing/04-Authentication_Testing/08-Testing_for_Weak_Security_Question_Answer.md` | auth-session |
| 4.4.9 | Testing for Weak Password Change or Reset Functional... | `4-Web_Application_Security_Testing/04-Authentication_Testing/09-Testing_for_Weak_Password_Change_or_Reset_Functionalities.md` | auth-session |

### 4.5

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 4.5.1 | Testing Directory Traversal File Include | `4-Web_Application_Security_Testing/05-Authorization_Testing/01-Testing_Directory_Traversal_File_Include.md` | tenant-isolation, idor |
| 4.5.2 | Testing for Bypassing Authorization Schema | `4-Web_Application_Security_Testing/05-Authorization_Testing/02-Testing_for_Bypassing_Authorization_Schema.md` | tenant-isolation, idor |
| 4.5.3 | Testing for Privilege Escalation | `4-Web_Application_Security_Testing/05-Authorization_Testing/03-Testing_for_Privilege_Escalation.md` | tenant-isolation, idor |
| 4.5.4 | Testing for Insecure Direct Object References | `4-Web_Application_Security_Testing/05-Authorization_Testing/04-Testing_for_Insecure_Direct_Object_References.md` | tenant-isolation, idor |
| 4.5.5 | Testing for OAuth Weaknesses | `4-Web_Application_Security_Testing/05-Authorization_Testing/05-Testing_for_OAuth_Weaknesses.md` | tenant-isolation, idor, oauth-gmail |

### 4.6

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 4.6.1 | Testing for Session Management Schema | `4-Web_Application_Security_Testing/06-Session_Management_Testing/01-Testing_for_Session_Management_Schema.md` | session-jwt |
| 4.6.10 | Testing JSON Web Tokens | `4-Web_Application_Security_Testing/06-Session_Management_Testing/10-Testing_JSON_Web_Tokens.md` | session-jwt |
| 4.6.11 | Testing for Concurrent Sessions | `4-Web_Application_Security_Testing/06-Session_Management_Testing/11-Testing_for_Concurrent_Sessions.md` | session-jwt |
| 4.6.2 | Testing for Cookies Attributes | `4-Web_Application_Security_Testing/06-Session_Management_Testing/02-Testing_for_Cookies_Attributes.md` | session-jwt |
| 4.6.3 | Testing for Session Fixation | `4-Web_Application_Security_Testing/06-Session_Management_Testing/03-Testing_for_Session_Fixation.md` | session-jwt |
| 4.6.4 | Testing for Exposed Session Variables | `4-Web_Application_Security_Testing/06-Session_Management_Testing/04-Testing_for_Exposed_Session_Variables.md` | session-jwt |
| 4.6.5 | Testing for Cross Site Request Forgery | `4-Web_Application_Security_Testing/06-Session_Management_Testing/05-Testing_for_Cross_Site_Request_Forgery.md` | session-jwt |
| 4.6.6 | Testing for Logout Functionality | `4-Web_Application_Security_Testing/06-Session_Management_Testing/06-Testing_for_Logout_Functionality.md` | session-jwt |
| 4.6.7 | Testing Session Timeout | `4-Web_Application_Security_Testing/06-Session_Management_Testing/07-Testing_Session_Timeout.md` | session-jwt |
| 4.6.8 | Testing for Session Puzzling | `4-Web_Application_Security_Testing/06-Session_Management_Testing/08-Testing_for_Session_Puzzling.md` | session-jwt |
| 4.6.9 | Testing for Session Hijacking | `4-Web_Application_Security_Testing/06-Session_Management_Testing/09-Testing_for_Session_Hijacking.md` | session-jwt |

### 4.7

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 4.7.1 | Testing for Reflected Cross Site Scripting | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/01-Testing_for_Reflected_Cross_Site_Scripting.md` | input-validation |
| 4.7.10 | Testing for IMAP SMTP Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/10-Testing_for_IMAP_SMTP_Injection.md` | input-validation |
| 4.7.11 | Testing for Code Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/11-Testing_for_Code_Injection.md` | input-validation |
| 4.7.12 | Testing for Command Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/12-Testing_for_Command_Injection.md` | input-validation |
| 4.7.13 | Testing for Format String Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/13-Testing_for_Format_String_Injection.md` | input-validation |
| 4.7.14 | Testing for Incubated Vulnerability | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/14-Testing_for_Incubated_Vulnerability.md` | input-validation |
| 4.7.15 | Testing for HTTP Response Splitting | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/15-Testing_for_HTTP_Response_Splitting.md` | input-validation |
| 4.7.16 | Testing for HTTP Request Smuggling | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/16-Testing_for_HTTP_Request_Smuggling.md` | input-validation |
| 4.7.17 | Testing for Host Header Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/17-Testing_for_Host_Header_Injection.md` | cors-headers, deployment-exposure, input-validation |
| 4.7.18 | Testing for Server-side Template Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/18-Testing_for_Server-side_Template_Injection.md` | input-validation |
| 4.7.19 | Testing for Server-Side Request Forgery | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/19-Testing_for_Server-Side_Request_Forgery.md` | input-validation |
| 4.7.2 | Testing for Stored Cross Site Scripting | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/02-Testing_for_Stored_Cross_Site_Scripting.md` | input-validation |
| 4.7.20 | Testing for Mass Assignment | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/20-Testing_for_Mass_Assignment.md` | input-validation |
| 4.7.21 | Testing for CSV Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/21-Testing_for_CSV_Injection.md` | input-validation |
| 4.7.3 | Testing for HTTP Verb Tampering | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/03-Testing_for_HTTP_Verb_Tampering.md` | input-validation |
| 4.7.4 | Testing for HTTP Parameter Pollution | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/04-Testing_for_HTTP_Parameter_Pollution.md` | input-validation |
| 4.7.5 | Testing for SQL Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection.md` | input-validation |
| 4.7.6 | Testing for LDAP Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/06-Testing_for_LDAP_Injection.md` | input-validation |
| 4.7.7 | Testing for XML Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/07-Testing_for_XML_Injection.md` | input-validation |
| 4.7.8 | Testing for SSI Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/08-Testing_for_SSI_Injection.md` | input-validation |
| 4.7.9 | Testing for XPath Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/09-Testing_for_XPath_Injection.md` | input-validation |

### 4.8

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 4.8.1 | Testing for Improper Error Handling | `4-Web_Application_Security_Testing/08-Testing_for_Error_Handling/01-Testing_For_Improper_Error_Handling.md` | error-logging |
| 4.8.2 | Testing for Stack Traces | `4-Web_Application_Security_Testing/08-Testing_for_Error_Handling/02-Testing_for_Stack_Traces.md` | error-logging |

### 4.9

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 4.9.1 | Testing for Weak Transport Layer Security | `4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/01-Testing_for_Weak_Transport_Layer_Security.md` | crypto-tls |
| 4.9.2 | Testing for Padding Oracle | `4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/02-Testing_for_Padding_Oracle.md` | crypto-tls |
| 4.9.3 | Testing for Sensitive Information Sent via Unencrypt... | `4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/03-Testing_for_Sensitive_Information_Sent_via_Unencrypted_Channels.md` | crypto-tls |
| 4.9.4 | Testing for Weak Cryptographic Primitives | `4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/04-Testing_for_Weak_Cryptographic_Primitives.md` | crypto-tls |

### 4.10

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 4.10.0 | Introduction to Business Logic | `4-Web_Application_Security_Testing/10-Business_Logic_Testing/00-Introduction_to_Business_Logic.md` | info-leakage, business-logic |
| 4.10.1 | Test Business Logic Data Validation | `4-Web_Application_Security_Testing/10-Business_Logic_Testing/01-Test_Business_Logic_Data_Validation.md` | info-leakage, business-logic |
| 4.10.10 | Test Payment Functionality | `4-Web_Application_Security_Testing/10-Business_Logic_Testing/10-Test-Payment-Functionality.md` | info-leakage, stripe-payments |
| 4.10.2 | Test Ability to Forge Requests | `4-Web_Application_Security_Testing/10-Business_Logic_Testing/02-Test_Ability_to_Forge_Requests.md` | info-leakage, business-logic |
| 4.10.3 | Test Integrity Checks | `4-Web_Application_Security_Testing/10-Business_Logic_Testing/03-Test_Integrity_Checks.md` | info-leakage, business-logic |
| 4.10.4 | Test for Process Timing | `4-Web_Application_Security_Testing/10-Business_Logic_Testing/04-Test_for_Process_Timing.md` | info-leakage, business-logic |
| 4.10.5 | Test Number of Times a Function Can Be Used Limits | `4-Web_Application_Security_Testing/10-Business_Logic_Testing/05-Test_Number_of_Times_a_Function_Can_Be_Used_Limits.md` | info-leakage, business-logic |
| 4.10.6 | Testing for the Circumvention of Work Flows | `4-Web_Application_Security_Testing/10-Business_Logic_Testing/06-Testing_for_the_Circumvention_of_Work_Flows.md` | info-leakage, business-logic |
| 4.10.7 | Test Defenses Against Application Misuse | `4-Web_Application_Security_Testing/10-Business_Logic_Testing/07-Test_Defenses_Against_Application_Misuse.md` | info-leakage, business-logic |
| 4.10.8 | Test Upload of Unexpected File Types | `4-Web_Application_Security_Testing/10-Business_Logic_Testing/08-Test_Upload_of_Unexpected_File_Types.md` | info-leakage, file-upload |
| 4.10.9 | Test Upload of Malicious Files | `4-Web_Application_Security_Testing/10-Business_Logic_Testing/09-Test_Upload_of_Malicious_Files.md` | info-leakage, file-upload |

### 4.11

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 4.11.1 | Testing for DOM-Based Cross Site Scripting | `4-Web_Application_Security_Testing/11-Client-side_Testing/01-Testing_for_DOM-based_Cross_Site_Scripting.md` | info-leakage, client-xss |
| 4.11.10 | Testing WebSockets | `4-Web_Application_Security_Testing/11-Client-side_Testing/10-Testing_WebSockets.md` | info-leakage, websockets, client-xss |
| 4.11.11 | Testing Web Messaging | `4-Web_Application_Security_Testing/11-Client-side_Testing/11-Testing_Web_Messaging.md` | info-leakage, client-xss |
| 4.11.12 | Testing Browser Storage | `4-Web_Application_Security_Testing/11-Client-side_Testing/12-Testing_Browser_Storage.md` | info-leakage, browser-storage, client-xss |
| 4.11.13 | Testing for Cross Site Script Inclusion | `4-Web_Application_Security_Testing/11-Client-side_Testing/13-Testing_for_Cross_Site_Script_Inclusion.md` | info-leakage, client-xss |
| 4.11.14 | Testing for Reverse Tabnabbing | `4-Web_Application_Security_Testing/11-Client-side_Testing/14-Testing_for_Reverse_Tabnabbing.md` | info-leakage, client-xss |
| 4.11.15 | Testing for Client-side Template Injection | `4-Web_Application_Security_Testing/11-Client-side_Testing/15-Testing_for_Client-Side_Template_Injection.md` | info-leakage, client-xss |
| 4.11.2 | Testing for JavaScript Execution | `4-Web_Application_Security_Testing/11-Client-side_Testing/02-Testing_for_JavaScript_Execution.md` | frontend-leakage, source-maps, client-xss |
| 4.11.3 | Testing for HTML Injection | `4-Web_Application_Security_Testing/11-Client-side_Testing/03-Testing_for_HTML_Injection.md` | info-leakage, client-xss |
| 4.11.4 | Testing for Client-side URL Redirect | `4-Web_Application_Security_Testing/11-Client-side_Testing/04-Testing_for_Client-side_URL_Redirect.md` | info-leakage, client-xss |
| 4.11.5 | Testing for CSS Injection | `4-Web_Application_Security_Testing/11-Client-side_Testing/05-Testing_for_CSS_Injection.md` | info-leakage, client-xss |
| 4.11.6 | Testing for Client-side Resource Manipulation | `4-Web_Application_Security_Testing/11-Client-side_Testing/06-Testing_for_Client-side_Resource_Manipulation.md` | info-leakage, client-xss |
| 4.11.7 | Testing Cross Origin Resource Sharing | `4-Web_Application_Security_Testing/11-Client-side_Testing/07-Testing_Cross_Origin_Resource_Sharing.md` | info-leakage, client-xss |
| 4.11.8 | Testing for Cross Site Flashing | `4-Web_Application_Security_Testing/11-Client-side_Testing/08-Testing_for_Cross_Site_Flashing.md` | info-leakage, client-xss |
| 4.11.9 | Testing for Clickjacking | `4-Web_Application_Security_Testing/11-Client-side_Testing/09-Testing_for_Clickjacking.md` | info-leakage, client-xss |

### 4.12

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 4.12.0 | API Testing Overview | `4-Web_Application_Security_Testing/12-API_Testing/00-API_Testing_Overview.md` | info-leakage, api-exposure, tenant-isolation |
| 4.12.1 | API Reconnaissance | `4-Web_Application_Security_Testing/12-API_Testing/01-API_Reconnaissance.md` | info-leakage, api-exposure, tenant-isolation |
| 4.12.2 | API Broken Object Level Authorization | `4-Web_Application_Security_Testing/12-API_Testing/02-API_Broken_Object_Level_Authorization.md` | info-leakage, tenant-isolation, idor, api-exposure |
| 4.12.3 | Testing for Excessive Data Exposure | `4-Web_Application_Security_Testing/12-API_Testing/03-Testing_for_Excessive_Data_Exposure.md` | info-leakage, api-exposure, tenant-isolation |
| 4.12.4 | API Broken Function Level Authorization | `4-Web_Application_Security_Testing/12-API_Testing/04-API_Broken_Function_Level_Authorization.md` | info-leakage, tenant-isolation, idor, api-exposure |
| 4.12.99 | Testing GraphQL | `4-Web_Application_Security_Testing/12-API_Testing/99-Testing_GraphQL.md` | info-leakage, api-exposure, tenant-isolation |

### 5.5

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 5.5.1 | Testing for OAuth Authorization Server Weaknesses | `4-Web_Application_Security_Testing/05-Authorization_Testing/05.1-Testing_for_OAuth_Authorization_Server_Weaknesses.md` | tenant-isolation, idor, oauth-gmail |
| 5.5.2 | Testing for OAuth Client Weaknesses | `4-Web_Application_Security_Testing/05-Authorization_Testing/05.2-Testing_for_OAuth_Client_Weaknesses.md` | tenant-isolation, idor, oauth-gmail |

### 7.5

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 7.5.1 | Testing for Oracle | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.1-Testing_for_Oracle.md` | — |
| 7.5.2 | Testing for MySQL | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.2-Testing_for_MySQL.md` | — |
| 7.5.3 | Testing for SQL Server | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.3-Testing_for_SQL_Server.md` | — |
| 7.5.4 | Testing PostgreSQL | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.4-Testing_PostgreSQL.md` | — |
| 7.5.5 | Testing for MS Access | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.5-Testing_for_MS_Access.md` | — |
| 7.5.6 | Testing for NoSQL Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.6-Testing_for_NoSQL_Injection.md` | — |
| 7.5.7 | Testing for ORM Injection | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.7-Testing_for_ORM_Injection.md` | — |
| 7.5.8 | Testing for Client-side | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.8-Testing_for_Client-side.md` | — |

### 7.11

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 7.11.1 | Testing for File Inclusion | `4-Web_Application_Security_Testing/07-Input_Validation_Testing/11.1-Testing_for_File_Inclusion.md` | — |

### 11.1

| ID | Test | Local leaf | Fikiri tags |
|----|------|------------|-------------|
| 11.1.1 | Testing for Self DOM Based Cross Site Scripting | `4-Web_Application_Security_Testing/11-Client-side_Testing/01.1-Testing_for_Self_DOM_Based_Cross_Site_Scripting.md` | — |

## Appendix & reporting

- **Reporting** — `owasp-wstg/5-Reporting.md`
- **404 - Not Found** — `owasp-wstg/5-Reporting/01-Reporting_Structure.md`
- **404 - Not Found** — `owasp-wstg/5-Reporting/02-Naming_Schemes.md`
- **Appendix** — `owasp-wstg/6-Appendix.md`
- **404 - Not Found** — `owasp-wstg/6-Appendix/A-Testing_Tools_Resource.md`
- **404 - Not Found** — `owasp-wstg/6-Appendix/B-Suggested_Reading.md`
- **404 - Not Found** — `owasp-wstg/6-Appendix/C-Fuzzing.md`
- **404 - Not Found** — `owasp-wstg/6-Appendix/D-Encoded_Injection.md`
- **404 - Not Found** — `owasp-wstg/6-Appendix/E-History.md`
- **404 - Not Found** — `owasp-wstg/6-Appendix/F-Leveraging_Dev_Tools.md`

## Related repo docs (not WSTG)

- `docs/SECURITY_ASSESSMENT.md` — prior Fikiri security notes
- `docs/ADMIN_ROUTES_STRATEGY.md` — admin RBAC direction
- `docs/CURSOR_QUALITY_GATE.md` — contract-table audit protocol

---

*Generated for offline audit planning. Live canonical source: [OWASP WSTG latest](https://owasp.org/www-project-web-security-testing-guide/latest/).*