```markdown
---
title: SOP: Customer Satisfaction Survey Post-Claims
type: sop
tags: [customer satisfaction, survey, claims, feedback, post-claim, quality assurance, procedure]
effective_date: 2024-03-01
---

# SOP: Customer Satisfaction Survey Post-Claims

## 1. Overview and Purpose

This Standard Operating Procedure (SOP) outlines the process for deploying and analyzing Customer Satisfaction Surveys (CSS) after a claim has been formally closed. The primary purpose of this procedure is to gather direct feedback from claimants regarding their experience with the claims process, the service provided by claims agents, and the overall resolution of their claim. This feedback is critical for continuous improvement, identifying areas of excellence, and addressing deficiencies in our claims handling operations.

## 2. Scope

This SOP applies to all closed claims across all product lines (e.g., auto, home, liability). It covers the automated and manual triggering of surveys, survey distribution, data collection, preliminary analysis, and reporting. This procedure applies to all claims personnel, quality assurance teams, and IT support staff involved in the claims management system and survey platform.

**Exclusions:** This SOP does not cover the design or creation of the survey instrument itself, nor does it detail the comprehensive long-term strategic analysis of consolidated survey data (which is handled by the Customer Experience department). It focuses solely on the operational workflow of deploying and gathering post-claim feedback.

## 3. Definitions

*   **CSS:** Customer Satisfaction Survey.
*   **Claim Closure:** The formal process by which a claim file is marked as complete and inactive in the Claims Management System (CMS), signifying that all required actions, payments, and communications have concluded.
*   **CMS:** Claims Management System – The primary software application used to process and manage customer claims.
*   **Survey Platform:** The third-party software used for survey deployment, data collection, and basic reporting (e.g., Qualtrics, SurveyMonkey Enterprise).
*   **Claimant:** The individual who filed the claim and is the recipient of the CSS.
*   **Response Rate:** The percentage of distributed surveys that are completed and returned.

## 4. Main Content: Procedure

### 4.1. Claim Closure and Survey Trigger

1.  **Automated Trigger (Preferred Method):**
    *   **Action:** Upon formal closure of a claim in the CMS (status changed to "Closed - Resolved" or "Closed - Paid"), the system will automatically trigger a survey request.
    *   **Decision Logic:** A survey is triggered unless the claim falls under a predefined exclusion category (see Section 4.1.3).
    *   **System Integration:** The CMS sends a secure API call to the Survey Platform containing the claimant's preferred contact method (email, SMS) and claim identifier.
2.  **Manual Trigger (Exception Based):**
    *   **Action:** If automated trigger fails or if a specific claim requires immediate feedback outside the standard cycle, a claims supervisor or manager may manually initiate a survey.
    *   **Authorization:** Manual triggers require approval from a Claims Team Lead or higher.
    *   **Procedure:** Navigate to the "Survey Trigger" module within the CMS, select the claim, choose "Manual Survey Request," and input claimant contact details.
3.  **Exclusion Criteria for Survey Trigger:**
    *   Claims marked as "Fraudulent Claim" or "Claim Denied - Policy Exclusion."
    *   Claims where the claimant explicitly opted out of future communications during the claims process.
    *   Claims with a subrogation status of "Active" (surveys will be sent after subrogation is fully resolved).
    *   Claims involving litigation where the legal department advises against contact.
    *   Claims from identified "Problematic Callers" or individuals who have exhibited abusive behavior, as flagged in the CMS.
    *   Claims closed within the last 30 days for the same claimant (to prevent survey fatigue).

### 4.2. Survey Distribution

1.  **Delay Period:** Surveys are distributed 24-48 hours after the claim closure timestamp to allow for system synchronization and final internal reviews.
2.  **Method:** Surveys are sent via the claimant's preferred communication method recorded in the CMS (email is default, SMS if opted-in).
3.  **Content:**
    *   Email/SMS will include a personalized greeting, the claim number for reference, and a direct link to the secure online survey.
    *   The message will clearly state the purpose of the survey (feedback for improvement) and estimated completion time (e.g., "This survey will take approximately 5-7 minutes to complete").
    *   Assurance of confidentiality will be provided.
4.  **Reminders:** One reminder email/SMS will be sent to non-responders 7 days after the initial invitation. No further reminders are sent to avoid inconvenience.

### 4.3. Data Collection and Monitoring

1.  **Platform:** All survey responses are collected and stored securely within the designated Survey Platform.
2.  **Anonymity:** Claimants are informed that their individual responses will be treated confidentially. While claim numbers are linked for internal analysis, direct claimant identification is restricted to specific quality assurance personnel.
3.  **Monitoring:** The Quality Assurance (QA) team is responsible for monitoring the overall response rate and identifying any significant anomalies in feedback trends. This includes a weekly review of the "Post-Claim Survey Dashboard" in the Survey Platform.

### 4.4. Analysis and Reporting

1.  **Automated Daily Report (ADR):**
    *   **Frequency:** Daily, at 09:00 AM EST.
    *   **Recipient:** Claims Team Leads, Claims Managers, QA Analysts.
    *   **Content:** Aggregated summary of responses received in the last 24 hours, average scores for key questions (e.g., "Agent Professionalism," "Speed of Resolution"), and a list of new verbatim comments flagged as "critical" or "negative" sentiment by the Survey Platform's AI.
2.  **Individual Response Review (Priority Cases):**
    *   **Criteria:** Any survey response where the overall satisfaction score is "Dissatisfied" (e.g., 1 or 2 out of 5) OR where verbatim comments indicate a significant negative experience (e.g., "unprofessional agent," "extreme delay," "misinformation").
    *   **Action:** QA Analysts or designated Claims Team Leads will review these specific responses within 1 business day of receipt.
    *   **Decision Logic:** If the feedback highlights a potentially actionable issue (e.g., agent error, systemic process failure, a "red flag" requiring follow-up), the QA Analyst will notify the relevant Claims Team Lead via an "Action Required" email, referencing the claim number and nature of the feedback.
3.  **Weekly Claims Performance Report (WCPR):**
    *   **Frequency:** Weekly, every Monday by 12:00 PM EST.
    *   **Recipient:** Senior Claims Management, Head of Customer Experience.
    *   **Content:** Trend analysis of CSS scores, identification of top 3 positive and top 3 negative feedback themes, comparison of performance against previous weeks/months, and recommendations for training or process adjustments based on feedback.

## 5. Requirements and Criteria

*   **Survey Platform Integration:** Must maintain a reliable, secure connection between the CMS and the Survey Platform.
*   **Claimant Data Accuracy:** Ensure claimant contact information in CMS is current and accurate to maximize delivery rates.
*   **Response Threshold for Action:** While all negative feedback is reviewed, systemic issues are typically identified when a specific negative theme appears in >10% of responses over a given week or month.
*   **Confidentiality:** All personnel handling survey data must adhere to strict data privacy and confidentiality protocols.

## 6. Exceptions

*   **System Outage:** In the event of a documented outage within the CMS or Survey Platform preventing automated survey triggers, a manual review process will be initiated by the QA team to capture outstanding claims for survey distribution once systems are restored. This catch-up will prioritize claims closed no more than 7 days prior to the outage resolution.
*   **Claimant Opt-in/Opt-out:** Specific requests from claimants to send or not send a survey should be honored and noted in the claim file, overriding automated processes.
*   **Multi-Claim Households:** If multiple claims are closed for the same household within a 30-day period, only one survey (for the most recent claim) should be distributed to prevent survey fatigue, unless otherwise specified by the claimant.

## 7. Examples

**Example 1: Automated Trigger**
*   Claim #12345678, for an auto accident, is marked "Closed - Paid" on 2024-03-15 at 11:00 AM EST.
*   System automatically triggers a survey request.
*   Email survey invitation sent to the claimant on 2024-03-16 at 10:00 AM EST.

**Example 2: Priority Individual Response Review**
*   A CSS for Claim #98765432 is submitted on 2024-03-20.
*   Overall satisfaction is rated 1/5.
*   Verbatim comment: "The agent, John Smith, was rude and unhelpful, and my repair took twice as long as promised."
*   QA Analyst receives the ADR. Within 1 business day, QA Analyst reviews the response, identifies it as a "critical" issue.
*   QA Analyst sends an "Action Required" email to the relevant Claims Team Lead (John Smith's supervisor), detailing the feedback and claim number. Team Lead will then investigate and address as per agent performance guidelines.

## 8. Evidence and Documentation

*   **CMS Log:** All survey trigger events (automated and manual) along with any exclusion reasons are logged in the respective claim's activity history within the CMS.
*   **Survey Platform Records:** Raw survey responses, timestamps, and claimant identifiers are stored in the Survey Platform.
*   **ADR & WCPR:** Daily and weekly reports are archived electronically on the shared network drive (e.g., `\\shared-data\claims\qa\surveys`).
*   **Action Required Emails:** Retained in the sender's and recipient's email inboxes for audit purposes.

## 9. Timelines

*   **Survey Distribution:** 24-48 hours post-claim closure.
*   **Reminder Survey:** 7 days after initial invitation (if no response).
*   **Individual Priority Response Review:** Within 1 business day of receipt.
*   **Automated Daily Report (ADR):** Daily by 09:00 AM EST.
*   **Weekly Claims Performance Report (WCPR):** Every Monday by 12:00 PM EST.
*   **Survey Response Window:** Claimants have 14 days from the initial invitation to complete the survey. After 14 days, the link will expire.
```
