```markdown
---
title: Claims Management System User Guide
type: reference
tags:
  - claims
  - claims processing
  - user guide
  - system
  - workflow
effective_date: 2023-10-26
---

# Claims Management System User Guide

## 1. Overview

This document serves as a comprehensive user guide for the internal Claims Management System (CMS), version 3.2.1. It provides detailed instructions and information on all functionalities, workflows, and procedures necessary for effectively processing and managing claims from initial intake to final resolution. The purpose of this guide is to ensure all claims processing personnel can efficiently navigate the system, adhere to established protocols, and leverage the system's capabilities to maintain high standards of accuracy, compliance, and customer service.

## 2. Scope

This User Guide applies to all employees involved in the claims lifecycle, including Claims Adjusters, Claims Processors, Claims Supervisors, and administrative support staff. It covers all modules and features within CMS related to:

*   New claim intake and registration
*   Claim assignment and re-assignment
*   Investigation and documentation
*   Benefit and eligibility determination
*   Reserve management
*   Payment processing
*   Correspondence generation
*   Reporting and analytics access

**Exclusions:** This guide does not cover system administration tasks, infrastructure maintenance, or detailed financial reconciliation procedures handled by the accounting department outside of the CMS payment module.

## 3. Definitions

*   **CMS:** Claims Management System – The proprietary software used for managing claims.
*   **Claim ID:** A unique alphanumeric identifier assigned to each claim upon initial registration.
*   **Claim Lifecycle:** The entire process from claim submission to closure.
*   **Insured:** The individual or entity covered by an insurance policy.
*   **Policyholder:** The individual or entity who owns the insurance policy.
*   **Adjuster:** The employee responsible for investigating and settling claims.
*   **Reserves:** Funds allocated for the potential future costs of a claim.
*   **FNOL:** First Notice Of Loss – The initial report of a claim.
*   **Subrogation:** The right for an insurer to pursue a third party that caused an insurance loss to the insured.
*   **Claim Status:** The current stage of a claim within the CMS workflow.

## 4. System Access and Login

### 4.1. Account Creation

New user accounts are provisioned by the IT Department upon request from a department manager via the IT Service Portal (ticket category: "New User Setup - CMS"). Account activation typically occurs within 24 business hours.

### 4.2. Login Procedure

1.  Navigate to the CMS login page: `https://cms.mycompany.com/login`
2.  Enter your assigned **Username** (typically your company email address).
3.  Enter your **Password**.
4.  Click the "Login" button.
5.  If prompted for Multi-Factor Authentication (MFA), follow the on-screen instructions (e.g., enter code from authenticator app or confirm via push notification).

### 4.3. Password Reset

If you forget your password, click the "Forgot Password?" link on the login page and follow the prompts. A reset link will be sent to your registered email address. For account lockout due to excessive failed attempts, contact the IT Help Desk.

## 5. Navigating the CMS Interface

### 5.1. Dashboard Overview

Upon successful login, users are directed to their personalized dashboard, which displays:

*   **My Open Claims:** A list of claims currently assigned to the user, sortable by status, urgency, or last updated date.
*   **Pending Tasks:** Notifications for actions requiring user attention (e.g., unread notes, pending approvals, overdue follow-ups).
*   **Key Performance Indicators (KPIs):** Individual claim processing metrics (e.g., average cycle time, pending workload count).
*   **System Announcements:** Important updates or scheduled maintenance notices.

### 5.2. Main Navigation Menu

The main navigation menu is located on the left-hand side of the screen and includes the following primary modules:

*   **Dashboard:** Returns to the main dashboard.
*   **Claims Search:** Accesses the claim search functionality.
*   **New Claim:** Initiates the First Notice of Loss (FNOL) process.
*   **Policy Lookup:** Allows searching for policy details in the integrated Policy Administration System.
*   **Reports:** Accesses predefined and custom report generation tools.
*   **Settings:** User-specific profile and notification preferences.
*   **Help:** Accesses this user guide and support contact information.

## 6. Claims Processing Workflow

### 6.1. New Claim Intake (FNOL)

#### 6.1.1. Initiate FNOL

1.  Click on "New Claim" from the main navigation menu.
2.  Select the **Claim Type** (e.g., Auto, Property, Liability, Workers' Comp).
3.  Input the **Policy Number** and click "Verify Policy". The system will automatically retrieve policyholder details if available.
    *   *Decision Logic:* If policy number is invalid or not found, an error message (`Policy Not Found: Please verify policy number or manually enter policyholder details`) will appear. Users must then manually input all policyholder and insured information.
4.  Enter the **Date of Loss** and **Time of Loss**.
5.  Provide a brief **Description of Loss**.
6.  Record **First Notice Date** and **Reporting Party** details.

#### 6.1.2. Capture Involved Parties

1.  Add **Insured Party** details (auto-populated if policy verified, otherwise manual entry).
2.  Add **Claimant Party** details (if different from Insured).
3.  Add **Third-Party** details (e.g., other drivers, damaged property owners).
4.  For each party, capture contact information (phone, email, address) and role.

#### 6.1.3. Attach Initial Documentation

Upload any available supporting documents provided during FNOL (e.g., police reports, photos, witness statements).
*   *Required Evidence:* At least one form of evidence confirming the incident, such as a loss description or incident report, is required to proceed.

#### 6.1.4. Submit FNOL

Review all entered information for accuracy. Click "Submit" to create the claim. A unique **Claim ID** will be generated and displayed.

### 6.2. Claim Assignment

Upon FNOL submission, the system automatically assigns the claim based on predefined rules:

*   **Rule 1: Geography:** Claims are assigned to adjusters covering the geographical region of loss.
*   **Rule 2: Claim Type Specialization:** If multiple adjusters cover a region, claims are assigned based on specialization (e.g., Auto Physical Damage, Bodily Injury).
*   **Rule 3: Workload Balancing:** The system prioritizes adjusters with the lowest current pending claim count within the qualified group.

*   *Override Process:* Supervisors can manually reassign claims using the "Reassign Claim" button within the Claim Details screen. Justification for reassignment is required.

### 6.3. Claim Investigation and Documentation

#### 6.3.1. Claim Details Page

Access a claim by entering its Claim ID in the "Claims Search" functionality or clicking on it from the dashboard. The Claim Details page is the central hub for all claim-related activities, organized into tabs:

*   **Overview:** Summary of claim status, parties, and key dates.
*   **Notes:** Chronological log of all interactions and investigative steps.
*   **Documents:** Repository for all uploaded and generated claim documents.
*   **Reserves:** Manages financial reserves for the claim.
*   **Payments:** Initiates and tracks claim payments.
*   **Activity Log:** Audit trail of all system actions taken on the claim.
*   **Subrogation:** Manages recovery efforts.

#### 6.3.2. Adding Notes

1.  Navigate to the "Notes" tab.
2.  Click "Add New Note."
3.  Select **Note Type** (e.g., Call Log, Email Correspondence, Investigation Memo, Internal Discussion).
4.  Enter the detailed note text.
5.  Relate note to **Party (Optional)**.
6.  Click "Save Note."
    *   *Requirement:* All verbal and written communication with external parties and significant internal decisions must be documented.

#### 6.3.3. Document Management

1.  Navigate to the "Documents" tab.
2.  Click "Upload Document."
3.  Select **Document Type** (e.g., Photos, Estimate, Police Report, Medical Records, Proof of Ownership).
4.  Browse and select the file from your local drive.
5.  Add a brief **Description**.
6.  Click "Upload."
    *   *File Size Limit:* Maximum 25MB per file. Accepted formats: PDF, JPG, PNG, DOCX, XLSX.

#### 6.3.4. Setting and Adjusting Reserves

1.  Navigate to the "Reserves" tab.
2.  Click "Add New Reserve" or "Adjust Existing Reserve."
3.  Select **Reserve Type** (e.g., Physical Damage, Medical, Loss of Use, ALE).
4.  Enter the **Reserve Amount** (USD).
5.  Provide a clear **Justification** for the reserve amount.
    *   *Decision Logic:* Any reserve increase above $10,000 or initial reserve setting above $25,000 requires supervisor approval. The system will automatically route for approval.
6.  Click "Save."

### 6.4. Benefit and Eligibility Determination

Adjusters must verify policy coverage and apply policy terms to the reported loss.

*   *Criteria:*
    *   **Active Policy Status:** Policy must be active at the Date of Loss.
    *   **Covered Peril:** The cause of loss must be explicitly covered by the policy.
    *   **Deductible Application:** Applicable deductibles must be identified and communicated.
    *   **Exclusions Check:** Review policy for any applicable exclusions that might negate coverage.

The "Policy Lookup" module provides direct access to policy terms and conditions.

### 6.5. Payment Processing

#### 6.5.1. Initiate Payment

1.  Navigate to the "Payments" tab within a claim.
2.  Click "Initiate New Payment."
3.  Select **Payee Type** (Insured, Claimant, Vendor, Lienholder).
4.  Search for or manually enter **Payee Name** and **Address**.
5.  Select **Payment Type** (e.g., Check, ACH, Wire Transfer).
6.  Enter **Payment Amount** (USD).
7.  Select **Payment Category** (e.g., Property Damage, Medical Bill, Loss of Income, Rental Reimbursement).
8.  Associate with relevant **Reserves** (optional, but recommended for accurate tracking).
9.  Add **Payment Description**.
10. Click "Submit for Approval."

#### 6.5.2. Payment Approval Workflow

*   *Decision Logic:*
    *   Payments up to $10,000: Auto-approved by system if sufficient reserves are available and no red flags identified.
    *   Payments between $10,001 and $50,000: Requires Claims Supervisor approval.
    *   Payments over $50,000: Requires Claims Manager approval.
    *   Payments with insufficient reserves: Automatically routed to the assigned Claims Adjuster's supervisor for review and potential reserve adjustment approval, regardless of amount.

Approvers receive a system notification and can approve/reject payments directly from their dashboards.

### 6.6. Correspondence

The CMS includes a correspondence module for generating standard letters and emails.

1.  Navigate to the "Correspondence" tab.
2.  Click "New Correspondence."
3.  Select **Correspondence Template** (e.g., Acknowledgment Letter, Reservation of Rights, Denial Letter, Settlement Offer).
4.  Select **Recipient Party**.
5.  The template will pre-populate with claim and party details. Review and make necessary edits.
6.  Generate as PDF for mailing or send via integrated email system.
    *   *Evidence:* A copy of all sent correspondence is automatically saved in the "Documents" tab.

### 6.7. Claim Closure

#### 6.7.1. Closure Criteria

A claim can be closed only when all of the following criteria are met:

*   All covered benefits have been paid.
*   All communications with parties have concluded.
*   All subrogation efforts have been finalized or determined to be futile.
*   All outstanding tasks and follow-ups are marked complete.
*   The claim's financial reserves are zero.
*   No further active investigation is required.

#### 6.7.2. Closure Procedure

1.  Ensure all outstanding items are addressed according to the closure criteria.
2.  Navigate to the "Overview" tab of the claim.
3.  Click "Close Claim."
4.  Select a **Closure Reason** (e.g., Settlement, Denial, Withdrawn, No Coverage, Statute of Limitations).
5.  Provide brief **Closure Summary**.
6.  Confirm closure. The claim status will change to "Closed" and will be archived after 90 days.

## 7. Reporting and Analytics

The "Reports" module provides access to various reports to monitor claims performance and identify trends.

*   **Standard Reports:**
    *   Claims by Status Report
    *   Claims by Adjuster Performance
    *   Average Cycle Time by Claim Type
    *   Claim Payment Breakdown
    *   Reserves vs. Payout Report
*   **Custom Report Builder:** Allows users with appropriate permissions to create ad-hoc reports using various data fields.

All reports can be exported to CSV or PDF format.

## 8. Exceptions

### 8.1. Urgent Claims

Claims flagged as "Urgent" (e.g., catastrophic loss, litigated claims) are highlighted on dashboards and prioritize notification dispatch. They bypass standard approval limits for payment up to $10,000, requiring Claims Supervisor approval directly.

### 8.2. Out-of-Policy Claims

If a situation arises where a payment or action is required but falls outside standard policy coverage or system rules, an "Exception Request" must be submitted to the Department Manager. This request must include:

*   Claim ID
*   Detailed explanation of the exception requested
*   Justification for the deviation
*   Anticipated financial impact

An approved exception request, documented and attached to the claim, overrides standard system rules.

## 9. Timelines

*   **FNOL Processing:** All FNOLs must be entered into the system within 4 business hours of receipt.
*   **Initial Contact:** Insured and primary claimant contact within 24 business hours of claim assignment.
*   **Payment Processing:** Approved payments are disbursed within 3 business days.
*   **Documentation Upload:** All received documents must be uploaded within 1 business day of receipt.
*   **Claim Review:** Claims with open reserves must be reviewed and documented at least every 30 days.

## 10. Support and Feedback

For technical issues or system errors, contact the IT Help Desk via the IT Service Portal or call extension 5555.
For functional questions or suggestions for system enhancements, contact the Claims Operations Support team at `claims.support@mycompany.com`.
```
