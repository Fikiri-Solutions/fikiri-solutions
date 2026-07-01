<!-- source: https://owasp.org/www-project-web-security-testing-guide/latest/0-Foreword/ -->
<!-- scraped_at: 2026-06-05T04:30:00Z -->
# Foreword

The problem of insecure software is perhaps the most important technical challenge of our time. The dramatic rise of web applications enabling business, social networking etc has only compounded the requirements to establish a robust approach to writing and securing our internet, web applications, and data.

At the Open Worldwide Application Security Project® (OWASP®), we’re trying to make the world a place where insecure software is the anomaly, not the norm. The OWASP Testing Guide has an important role to play in solving this serious issue. It is vitally important that our approach to testing software for security issues is based on the principles of engineering and science. We need a consistent, repeatable and defined approach to testing web applications. A world without some minimal standards in terms of engineering and technology is a world in chaos.

It goes without saying that you can’t build a secure application without performing security testing on it. Testing is part of a wider approach to build a secure system. Many software development organizations do not include security testing as part of their standard software development process. What is even worse is that many security vendors deliver testing with varying degrees of quality and rigor.

Security testing, by itself, isn’t a particularly good stand alone measure of how secure an application is, because there are an infinite number of ways that an attacker might be able to make an application break, and it simply isn’t possible to test them all. We can’t hack ourselves secure as we only have a limited time to test and defend where an attacker does not have such constraints.

In conjunction with other OWASP projects such as the Code Review Guide, the Development Guide and tools such as [ZAP](https://www.zaproxy.org/), this is a great start towards building and maintaining secure applications. This Testing Guide will show you how to verify the security of your running application. I highly recommend using these guides as part of your application security initiatives.

## Why OWASP?

Creating a guide like this is a huge undertaking, requiring the expertise of hundreds of people around the world. There are many different ways to test for security flaws and this guide captures the consensus of the leading experts on how to perform this testing quickly, accurately, and efficiently. OWASP gives like minded security folks the ability to work together and form a leading practice approach to a security problem.

The importance of having this guide available in a completely free and open way is important for the foundation’s mission. It gives anyone the ability to understand the techniques used to test for common security issues. Security should not be a black art or closed secret that only a few can practice. It should be open to all and not exclusive to security practitioners but also QA, Developers and Technical Managers. The project to build this guide keeps this expertise in the hands of the people who need it - you, me and anyone that is involved in building software.

This guide must make its way into the hands of developers and software testers. There are not nearly enough application security experts in the world to make any significant dent in the overall problem. The initial responsibility for application security must fall on the shoulders of the developers because they write the code. It shouldn’t be a surprise that developers aren’t producing secure code if they’re not testing for it or consider the types of bugs which introduce vulnerability.

Keeping this information up to date is a critical aspect of this guide project. By adopting the wiki approach, the OWASP community can evolve and expand the information in this guide to keep pace with the fast moving application security threat landscape.

This Guide is a great testament to the passion and energy our members and project volunteers have for this subject. It shall certainly help to change the world a line of code at a time.

## Tailoring and Prioritizing

You should adopt this guide in your organization. You may need to tailor the information to match your organization’s technologies, processes, and organizational structure.

In general there are several different roles within organizations that may use this guide:

- Developers should use this guide to ensure that they are producing secure code. These tests should be a part of normal code and unit testing procedures.
- Software testers and QA should use this guide to expand the set of test cases they apply to applications. Catching these vulnerabilities early saves considerable time and effort later.
- Security specialists should use this guide in combination with other techniques as one way to verify that no security holes have been missed in an application.
- Project Managers should consider the reason this guide exists and that security issues are manifested via bugs in code and design.

The most important thing to remember when performing security testing is to continuously re-prioritize. There are infinite ways that an application could fail, and organizations always have limited testing time and resources. Be sure time and resources are spent wisely. Try to focus on the security holes that are a real risk to your business. Try to contextualize risk in terms of the application and its use cases.

This guide is best viewed as a set of techniques that you can use to find different types of security holes. But not all the techniques are equally important. Try to avoid using the guide as a checklist, new vulnerabilities are always manifesting and no guide can be an exhaustive list of “things to test for”, but rather a great place to start.

## The Role of Automated Tools

There are a number of companies selling automated security analysis and testing tools. Remember the limitations of these tools so that you can use them for what they’re good at. As Michael Howard put it at the 2006 OWASP AppSec Conference in Seattle, “Tools do not make software secure! They help scale the process and help enforce policy.”

Most importantly, these tools are generic - meaning that they are not designed for your custom code, but for applications in general. That means that while they can find some generic problems, they do not have enough knowledge of your application to allow them to detect most flaws. In my experience, the most serious security issues are the ones that are not generic, but deeply intertwined in your business logic and custom application design.

These tools can also be very useful, since they do find lots of potential issues. While running the tools doesn’t take much time, each one of the potential problems takes time to investigate and verify. If the goal is to find and eliminate the most serious flaws as quickly as possible, consider whether your time is best spent with automated tools or with the techniques described in this guide. Still, these tools are certainly part of a well-balanced application security program. Used wisely, they can support your overall processes to produce more secure code.

## Call to Action

If you’re building, designing or testing software, we strongly encourage you to get familiar with the security testing guidance in this document. It is a great road map for testing the most common issues that applications are facing today, but it is not exhaustive. If you find errors, please add a note to the discussion page or make the change yourself. You’ll be helping thousands of others who use this guide.

Please consider [joining us](https://owasp.org/membership/) as an individual or corporate member so that we can continue to produce materials like this testing guide and all the other great projects at OWASP.

Thank you to all the past and future contributors to this guide, your work will help to make applications worldwide more secure.

Open Worldwide Application Security Project and OWASP are registered trademarks of the OWASP Foundation, Inc.

------------------------------------------------------------------------

<div class="repo">

</div>

<div class="github-buttons">

<a href="https://github.com/OWASP/wstg/subscription" class="github-button" data-icon="octicon-eye" data-size="large" data-show-count="true" aria-label="Watch on GitHub">Watch</a> <a href="https://github.com/OWASP/wstg" class="github-button" data-icon="octicon-star" data-size="large" data-show-count="true" aria-label="Star on GitHub">Star</a>

</div>

<div class="sidebar" role="complementary">

<div class="owasp-sidebar-top">

**The OWASP<sup>®</sup> Foundation** works to improve the security of software through its community-led open source software projects, hundreds of chapters worldwide, tens of thousands of members, and by hosting local and global conferences.

</div>

## [WSTG Contents](https://owasp.org/www-project-web-security-testing-guide/latest/)

- [0. Foreword](https://owasp.org/www-project-web-security-testing-guide/latest/0-Foreword/README)
- [1. Frontispiece](https://owasp.org/www-project-web-security-testing-guide/latest/1-Frontispiece/)
- [2. Introduction](https://owasp.org/www-project-web-security-testing-guide/latest/2-Introduction/)
- [2.1 The OWASP Testing Project](https://owasp.org/www-project-web-security-testing-guide/latest/2-Introduction/README#the-owasp-testing-project)
- [2.2 Principles of Testing](https://owasp.org/www-project-web-security-testing-guide/latest/2-Introduction/README#principles-of-testing)
- [2.3 Testing Techniques Explained](https://owasp.org/www-project-web-security-testing-guide/latest/2-Introduction/README#testing-techniques-explained)
- [2.4 Manual Inspections and Reviews](https://owasp.org/www-project-web-security-testing-guide/latest/2-Introduction/README#manual-inspections-and-reviews)
- [2.5 Threat Modeling](https://owasp.org/www-project-web-security-testing-guide/latest/2-Introduction/README#threat-modeling)
- [2.6 Source Code Review](https://owasp.org/www-project-web-security-testing-guide/latest/2-Introduction/README#source-code-review)
- [2.7 Penetration Testing](https://owasp.org/www-project-web-security-testing-guide/latest/2-Introduction/README#penetration-testing)
- [2.8 The Need for a Balanced Approach](https://owasp.org/www-project-web-security-testing-guide/latest/2-Introduction/README#the-need-for-a-balanced-approach)
- [2.9 Deriving Security Test Requirements](https://owasp.org/www-project-web-security-testing-guide/latest/2-Introduction/README#deriving-security-test-requirements)
- [2.10 Security Tests Integrated in Development and Testing Workflows](https://owasp.org/www-project-web-security-testing-guide/latest/2-Introduction/README#security-tests-integrated-in-development-and-testing-workflows)
- [2.11 Security Test Data Analysis and Reporting](https://owasp.org/www-project-web-security-testing-guide/latest/2-Introduction/README#security-test-data-analysis-and-reporting)
- [3. The OWASP Testing Framework](https://owasp.org/www-project-web-security-testing-guide/latest/3-The_OWASP_Testing_Framework/)
- [3.1 The Web Security Testing Framework](https://owasp.org/www-project-web-security-testing-guide/latest/3-The_OWASP_Testing_Framework/0-The_Web_Security_Testing_Framework)
- [3.2 Phase 1 Before Development Begins](https://owasp.org/www-project-web-security-testing-guide/latest/3-The_OWASP_Testing_Framework/0-The_Web_Security_Testing_Framework#phase-1-before-development-begins)
- [3.3 Phase 2 During Definition and Design](https://owasp.org/www-project-web-security-testing-guide/latest/3-The_OWASP_Testing_Framework/0-The_Web_Security_Testing_Framework#phase-2-during-definition-and-design)
- [3.4 Phase 3 During Development](https://owasp.org/www-project-web-security-testing-guide/latest/3-The_OWASP_Testing_Framework/0-The_Web_Security_Testing_Framework#phase-3-during-development)
- [3.5 Phase 4 During Deployment](https://owasp.org/www-project-web-security-testing-guide/latest/3-The_OWASP_Testing_Framework/0-The_Web_Security_Testing_Framework#phase-4-during-deployment)
- [3.6 Phase 5 During Maintenance and Operations](https://owasp.org/www-project-web-security-testing-guide/latest/3-The_OWASP_Testing_Framework/0-The_Web_Security_Testing_Framework#phase-5-during-maintenance-and-operations)
- [3.7 A Typical SDLC Testing Workflow](https://owasp.org/www-project-web-security-testing-guide/latest/3-The_OWASP_Testing_Framework/0-The_Web_Security_Testing_Framework#a-typical-sdlc-testing-workflow)
- [3.8 Penetration Testing Methodologies](https://owasp.org/www-project-web-security-testing-guide/latest/3-The_OWASP_Testing_Framework/1-Penetration_Testing_Methodologies)
- [4. Web Application Security Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/)
- [4.0 Introduction and Objectives](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/00-Introduction_and_Objectives/README)
- [4.1 Information Gathering](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/README)
- [4.1.1 Conduct Search Engine Discovery Reconnaissance for Information Leakage](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/01-Conduct_Search_Engine_Discovery_Reconnaissance_for_Information_Leakage)
- [4.1.2 Fingerprint Web Server](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/02-Fingerprint_Web_Server)
- [4.1.3 Review Webserver Metafiles for Information Leakage](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/03-Review_Webserver_Metafiles_for_Information_Leakage)
- [4.1.4 Attack Surface Identification](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/04-Attack_Surface_Identification)
- [4.1.5 Review Web Page Content for Information Leakage](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/05-Review_Web_Page_Content_for_Information_Leakage)
- [4.1.6 Identify Application Entry Points](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/06-Identify_Application_Entry_Points)
- [4.1.7 Map Execution Paths Through Application](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/07-Map_Execution_Paths_Through_Application)
- [4.1.8 Fingerprint Web Application Framework](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/08-Fingerprint_Web_Application_Framework)
- [4.1.9 Fingerprint Web Application](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/09-Fingerprint_Web_Application)
- [4.1.10 Map Application Architecture](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/10-Map_Application_Architecture)
- [4.2 Configuration and Deployment Management Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/README)
- [4.2.1 Test Network Infrastructure Configuration](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/01-Test_Network_Infrastructure_Configuration)
- [4.2.2 Test Application Platform Configuration](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/02-Test_Application_Platform_Configuration)
- [4.2.3 Test File Extensions Handling for Sensitive Information](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/03-Test_File_Extensions_Handling_for_Sensitive_Information)
- [4.2.4 Review Old Backup and Unreferenced Files for Sensitive Information](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/04-Review_Old_Backup_and_Unreferenced_Files_for_Sensitive_Information)
- [4.2.5 Enumerate Infrastructure and Application Admin Interfaces](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/05-Enumerate_Infrastructure_and_Application_Admin_Interfaces)
- [4.2.6 Test HTTP Methods](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/06-Test_HTTP_Methods)
- [4.2.7 Test HTTP Strict Transport Security](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/07-Test_HTTP_Strict_Transport_Security)
- [4.2.8 Test RIA Cross Domain Policy](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/08-Test_RIA_Cross_Domain_Policy)
- [4.2.9 Test File Permission](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/09-Test_File_Permission)
- [4.2.10 Test for Subdomain Takeover](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/10-Test_for_Subdomain_Takeover)
- [4.2.11 Test Cloud Storage](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/11-Test_Cloud_Storage)
- [4.2.12 Test for Content Security Policy](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/12-Test_for_Content_Security_Policy)
- [4.2.13 Test for Path Confusion](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/13-Test_for_Path_Confusion)
- [4.2.14 Test Other HTTP Security Header Misconfigurations](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/14-Test_Other_HTTP_Security_Header_Misconfigurations)
- [4.3 Identity Management Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/03-Identity_Management_Testing/README)
- [4.3.1 Test Role Definitions](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/03-Identity_Management_Testing/01-Test_Role_Definitions)
- [4.3.2 Test User Registration Process](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/03-Identity_Management_Testing/02-Test_User_Registration_Process)
- [4.3.3 Test Account Provisioning Process](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/03-Identity_Management_Testing/03-Test_Account_Provisioning_Process)
- [4.3.4 Testing for Account Enumeration and Guessable User Account](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/03-Identity_Management_Testing/04-Testing_for_Account_Enumeration_and_Guessable_User_Account)
- [4.3.5 Testing for Weak or Unenforced Username Policy](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/03-Identity_Management_Testing/05-Testing_for_Weak_or_Unenforced_Username_Policy)
- [4.4 Authentication Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/README)
- [4.4.1 Testing for Credentials Transported over an Encrypted Channel](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/01-Testing_for_Credentials_Transported_over_an_Encrypted_Channel)
- [4.4.2 Testing for Default Credentials](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/02-Testing_for_Default_Credentials)
- [4.4.3 Testing for Weak Lock Out Mechanism](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/03-Testing_for_Weak_Lock_Out_Mechanism)
- [4.4.4 Testing for Bypassing Authentication Schema](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/04-Testing_for_Bypassing_Authentication_Schema)
- [4.4.5 Testing for Vulnerable Remember Password](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/05-Testing_for_Vulnerable_Remember_Password)
- [4.4.6 Testing for Browser Cache Weaknesses](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/06-Testing_for_Browser_Cache_Weaknesses)
- [4.4.7 Testing for Weak Authentication Methods](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/07-Testing_for_Weak_Authentication_Methods)
- [4.4.8 Testing for Weak Security Question Answer](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/08-Testing_for_Weak_Security_Question_Answer)
- [4.4.9 Testing for Weak Password Change or Reset Functionalities](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/09-Testing_for_Weak_Password_Change_or_Reset_Functionalities)
- [4.4.10 Testing for Weaker Authentication in Alternative Channel](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/10-Testing_for_Weaker_Authentication_in_Alternative_Channel)
- [4.4.11 Testing Multi-Factor Authentication](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/11-Testing_Multi-Factor_Authentication)
- [4.5 Authorization Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/README)
- [4.5.1 Testing Directory Traversal File Include](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/01-Testing_Directory_Traversal_File_Include)
- [4.5.2 Testing for Bypassing Authorization Schema](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/02-Testing_for_Bypassing_Authorization_Schema)
- [4.5.3 Testing for Privilege Escalation](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/03-Testing_for_Privilege_Escalation)
- [4.5.4 Testing for Insecure Direct Object References](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/04-Testing_for_Insecure_Direct_Object_References)
- [4.5.5 Testing for OAuth Weaknesses](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/05-Testing_for_OAuth_Weaknesses)
- [4.5.5.1 Testing for OAuth Authorization Server Weaknesses](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/05.1-Testing_for_OAuth_Authorization_Server_Weaknesses)
- [4.5.5.2 Testing for OAuth Client Weaknesses](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/05.2-Testing_for_OAuth_Client_Weaknesses)
- [4.6 Session Management Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/README)
- [4.6.1 Testing for Session Management Schema](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/01-Testing_for_Session_Management_Schema)
- [4.6.2 Testing for Cookies Attributes](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/02-Testing_for_Cookies_Attributes)
- [4.6.3 Testing for Session Fixation](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/03-Testing_for_Session_Fixation)
- [4.6.4 Testing for Exposed Session Variables](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/04-Testing_for_Exposed_Session_Variables)
- [4.6.5 Testing for Cross Site Request Forgery](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/05-Testing_for_Cross_Site_Request_Forgery)
- [4.6.6 Testing for Logout Functionality](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/06-Testing_for_Logout_Functionality)
- [4.6.7 Testing Session Timeout](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/07-Testing_Session_Timeout)
- [4.6.8 Testing for Session Puzzling](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/08-Testing_for_Session_Puzzling)
- [4.6.9 Testing for Session Hijacking](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/09-Testing_for_Session_Hijacking)
- [4.6.10 Testing JSON Web Tokens](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/10-Testing_JSON_Web_Tokens)
- [4.6.11 Testing for Concurrent Sessions](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/11-Testing_for_Concurrent_Sessions)
- [4.7 Input Validation Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/README)
- [4.7.1 Testing for Reflected Cross Site Scripting](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/01-Testing_for_Reflected_Cross_Site_Scripting)
- [4.7.2 Testing for Stored Cross Site Scripting](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/02-Testing_for_Stored_Cross_Site_Scripting)
- [4.7.3 Testing for HTTP Verb Tampering](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/03-Testing_for_HTTP_Verb_Tampering)
- [4.7.4 Testing for HTTP Parameter Pollution](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/04-Testing_for_HTTP_Parameter_Pollution)
- [4.7.5 Testing for SQL Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection)
- [4.7.5.1 Testing for Oracle](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.1-Testing_for_Oracle)
- [4.7.5.2 Testing for MySQL](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.2-Testing_for_MySQL)
- [4.7.5.3 Testing for SQL Server](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.3-Testing_for_SQL_Server)
- [4.7.5.4 Testing PostgreSQL](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.4-Testing_PostgreSQL)
- [4.7.5.5 Testing for MS Access](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.5-Testing_for_MS_Access)
- [4.7.5.6 Testing for NoSQL Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.6-Testing_for_NoSQL_Injection)
- [4.7.5.7 Testing for ORM Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.7-Testing_for_ORM_Injection)
- [4.7.5.8 Testing for Client-side](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.8-Testing_for_Client-side)
- [4.7.6 Testing for LDAP Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/06-Testing_for_LDAP_Injection)
- [4.7.7 Testing for XML Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/07-Testing_for_XML_Injection)
- [4.7.8 Testing for SSI Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/08-Testing_for_SSI_Injection)
- [4.7.9 Testing for XPath Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/09-Testing_for_XPath_Injection)
- [4.7.10 Testing for IMAP SMTP Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/10-Testing_for_IMAP_SMTP_Injection)
- [4.7.11 Testing for Code Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/11-Testing_for_Code_Injection)
- [4.7.11.1 Testing for File Inclusion](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/11.1-Testing_for_File_Inclusion)
- [4.7.12 Testing for Command Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/12-Testing_for_Command_Injection)
- [4.7.13 Testing for Format String Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/13-Testing_for_Format_String_Injection)
- [4.7.14 Testing for Incubated Vulnerability](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/14-Testing_for_Incubated_Vulnerability)
- [4.7.15 Testing for HTTP Response Splitting](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/15-Testing_for_HTTP_Response_Splitting)
- [4.7.16 Testing for HTTP Request Smuggling](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/16-Testing_for_HTTP_Request_Smuggling)
- [4.7.17 Testing for Host Header Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/17-Testing_for_Host_Header_Injection)
- [4.7.18 Testing for Server-side Template Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/18-Testing_for_Server-side_Template_Injection)
- [4.7.19 Testing for Server-Side Request Forgery](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/19-Testing_for_Server-Side_Request_Forgery)
- [4.7.20 Testing for Mass Assignment](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/20-Testing_for_Mass_Assignment)
- [4.7.21 Testing for CSV Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/21-Testing_for_CSV_Injection)
- [4.8 Testing for Error Handling](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/08-Testing_for_Error_Handling/README)
- [4.8.1 Testing for Improper Error Handling](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/08-Testing_for_Error_Handling/01-Testing_For_Improper_Error_Handling)
- [4.8.2 Testing for Stack Traces](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/08-Testing_for_Error_Handling/02-Testing_for_Stack_Traces)
- [4.9 Testing for Weak Cryptography](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/README)
- [4.9.1 Testing for Weak Transport Layer Security](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/01-Testing_for_Weak_Transport_Layer_Security)
- [4.9.2 Testing for Padding Oracle](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/02-Testing_for_Padding_Oracle)
- [4.9.3 Testing for Sensitive Information Sent via Unencrypted Channels](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/03-Testing_for_Sensitive_Information_Sent_via_Unencrypted_Channels)
- [4.9.4 Testing for Weak Cryptographic Primitives](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/04-Testing_for_Weak_Cryptographic_Primitives)
- [4.10 Business Logic Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/README)
- [4.10.0 Introduction to Business Logic](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/00-Introduction_to_Business_Logic)
- [4.10.1 Test Business Logic Data Validation](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/01-Test_Business_Logic_Data_Validation)
- [4.10.2 Test Ability to Forge Requests](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/02-Test_Ability_to_Forge_Requests)
- [4.10.3 Test Integrity Checks](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/03-Test_Integrity_Checks)
- [4.10.4 Test for Process Timing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/04-Test_for_Process_Timing)
- [4.10.5 Test Number of Times a Function Can Be Used Limits](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/05-Test_Number_of_Times_a_Function_Can_Be_Used_Limits)
- [4.10.6 Testing for the Circumvention of Work Flows](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/06-Testing_for_the_Circumvention_of_Work_Flows)
- [4.10.7 Test Defenses Against Application Misuse](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/07-Test_Defenses_Against_Application_Misuse)
- [4.10.8 Test Upload of Unexpected File Types](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/08-Test_Upload_of_Unexpected_File_Types)
- [4.10.9 Test Upload of Malicious Files](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/09-Test_Upload_of_Malicious_Files)
- [4.10.10 Test Payment Functionality](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/10-Test-Payment-Functionality)
- [4.11 Client-side Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/README)
- [4.11.1 Testing for DOM-Based Cross Site Scripting](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/01-Testing_for_DOM-based_Cross_Site_Scripting)
- [4.11.1.1 Testing for Self DOM Based Cross-Site Scripting](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/01.1-Testing_for_Self_DOM_Based_Cross_Site_Scripting)
- [4.11.2 Testing for JavaScript Execution](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/02-Testing_for_JavaScript_Execution)
- [4.11.3 Testing for HTML Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/03-Testing_for_HTML_Injection)
- [4.11.4 Testing for Client-side URL Redirect](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/04-Testing_for_Client-side_URL_Redirect)
- [4.11.5 Testing for CSS Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/05-Testing_for_CSS_Injection)
- [4.11.6 Testing for Client-side Resource Manipulation](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/06-Testing_for_Client-side_Resource_Manipulation)
- [4.11.7 Testing Cross Origin Resource Sharing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/07-Testing_Cross_Origin_Resource_Sharing)
- [4.11.8 Testing for Cross Site Flashing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/08-Testing_for_Cross_Site_Flashing)
- [4.11.9 Testing for Clickjacking](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/09-Testing_for_Clickjacking)
- [4.11.10 Testing WebSockets](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/10-Testing_WebSockets)
- [4.11.11 Testing Web Messaging](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/11-Testing_Web_Messaging)
- [4.11.12 Testing Browser Storage](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/12-Testing_Browser_Storage)
- [4.11.13 Testing for Cross Site Script Inclusion](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/13-Testing_for_Cross_Site_Script_Inclusion)
- [4.11.14 Testing for Reverse Tabnabbing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/14-Testing_for_Reverse_Tabnabbing)
- [4.11.15 Testing for Client-side Template Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/15-Testing_for_Client-Side_Template_Injection)
- [4.12 API Testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/12-API_Testing/README)
- [4.12.0 API Testing Overview](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/12-API_Testing/00-API_Testing_Overview)
- [4.12.1 API Reconnaissance](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/12-API_Testing/01-API_Reconnaissance)
- [4.12.2 API Broken Object Level Authorization](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/12-API_Testing/02-API_Broken_Object_Level_Authorization)
- [4.12.3 Testing for Excessive Data Exposure](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/12-API_Testing/03-Testing_for_Excessive_Data_Exposure)
- [4.12.4 API Broken Function Level Authorization](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/12-API_Testing/04-API_Broken_Function_Level_Authorization)
- [4.12.99 Testing GraphQL](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/12-API_Testing/99-Testing_GraphQL)
- [5. Reporting](https://owasp.org/www-project-web-security-testing-guide/latest/5-Reporting/README)
- [5.1 Reporting Structure](https://owasp.org/www-project-web-security-testing-guide/latest/5-Reporting/01-Reporting_Structure)
- [5.2 Naming Schemes](https://owasp.org/www-project-web-security-testing-guide/latest/5-Reporting/02-Naming_Schemes)
- [Appendix A. Testing Tools Resource](https://owasp.org/www-project-web-security-testing-guide/latest/6-Appendix/A-Testing_Tools_Resource)
- [Appendix B. Suggested Reading](https://owasp.org/www-project-web-security-testing-guide/latest/6-Appendix/B-Suggested_Reading)
- [Appendix C. Fuzzing](https://owasp.org/www-project-web-security-testing-guide/latest/6-Appendix/C-Fuzzing)
- [Appendix D. Encoded Injection](https://owasp.org/www-project-web-security-testing-guide/latest/6-Appendix/D-Encoded_Injection)
- [Appendix E. History](https://owasp.org/www-project-web-security-testing-guide/latest/6-Appendix/E-History)
- [Appendix F. Leveraging Dev Tools](https://owasp.org/www-project-web-security-testing-guide/latest/6-Appendix/F-Leveraging_Dev_Tools)

<div class="owasp-sidebar-bottom">

### Upcoming OWASP Global Events

<div id="global-event-div">

</div>

</div>

</div>
