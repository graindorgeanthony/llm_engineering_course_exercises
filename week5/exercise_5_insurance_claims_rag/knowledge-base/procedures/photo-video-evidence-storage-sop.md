```markdown
---
title: SOP: Photo and Video Evidence Storage
type: sop
tags: [evidence, storage, photo, video, claims, documentation, media, digital assets]
effective_date: 2023-10-26
---

# SOP: Photo and Video Evidence Storage

## 1. Overview

This Standard Operating Procedure (SOP) outlines the guidelines and steps for the proper documentation, storage, and management of photo and video evidence submitted as part of insurance claims. Adhering to this SOP ensures evidence integrity, proper chain of custody, efficient retrieval, and compliance with data retention policies. This procedure is critical for supporting claim assessments, dispute resolution, and fraud prevention.

## 2. Purpose

The purpose of this SOP is to establish a standardized, secure, and accessible system for handling all visual media evidence associated with claims. This ensures:
*   Integrity and authenticity of evidence.
*   Compliance with privacy regulations and data security standards.
*   Efficient retrieval of visual evidence for claim adjusters, legal teams, and auditors.
*   Minimization of data loss or corruption.
*   Consistency in evidence handling across all claim types.

## 3. Scope

This SOP applies to all employees, contractors, and third-party vendors involved in receiving, processing, or managing claims that include photo or video evidence. This includes, but is not limited to:
*   Claim intake personnel
*   Claim adjusters
*   Investigators
*   Legal department staff

### 3.1. In-Scope

*   Photos and videos submitted by policyholders, third parties, or professional investigators.
*   Media captured via smartphones, digital cameras, drones, or surveillance systems.
*   Evidence relating to property damage, personal injury, liability, and other claim types.
*   Digital files in common formats (JPEG, PNG, MP4, MOV, etc.).

### 3.2. Out-of-Scope

*   Physical paper documents (covered by separate document management SOPs).
*   Audio-only evidence (specific handling may be outlined in other SOPs).
*   Evidence collected for non-claim related purposes (e.g., marketing materials).

## 4. Definitions

*   **Evidence Management System (EMS):** The designated secure digital platform for storing and managing all claim-related evidence.
*   **Claim ID:** The unique identifier assigned to each claim.
*   **Metadata:** Data providing information about other data, such as date created, device type, location (if embedded), and file size.
*   **Chain of Custody:** The chronological documentation showing the seizure, custody, control, transfer, analysis, and disposition of evidence.
*   **Redaction:** The process of obscuring sensitive or private information within a visual file.
*   **Digital Fingerprint (Hash Value):** A unique alphanumeric string generated from a digital file, used to verify its integrity.

## 5. Responsibilities

*   **Claim Intake/Adjuster:** Responsible for initial receipt, preliminary review, and secure upload of evidence to EMS.
*   **Data Management Team:** Responsible for system maintenance, access control, and ensuring data integrity and backup.
*   **Compliance Officer:** Responsible for ensuring adherence to legal and regulatory requirements for data storage.

## 6. Procedures for Photo and Video Evidence Storage

### 6.1. Receipt and Initial Review of Evidence

1.  **Acknowledge Receipt:** Upon receiving photo or video evidence (via email, portal upload, physical media, etc.), acknowledge receipt to the submitter within 24 business hours.
2.  **Preliminary Assessment:** Perform a quick review to ensure the files are accessible, relevant to the claim, and not overtly corrupted.
    *   *Criterion:* File opens correctly, content is visually discernible, and relates to the reported incident.
3.  **Virus Scan:** All incoming digital files from external sources must undergo an automated virus scan upon upload to the designated staging area. Files flagged for viruses must be quarantined and reported to IT security.
4.  **Verification of Claim ID:** Ensure the evidence can be clearly linked to a specific Claim ID. If not, contact the submitter for clarification.

### 6.2. Documenting Evidence Details

For each piece of photo or video evidence, the following metadata must be accurately recorded in the EMS linked to the corresponding Claim ID:

*   **Evidence Type:** Photo, Video, Series of Photos, Drone Footage, Surveillance.
*   **Submission Date:** Date the evidence was received.
*   **Date of Incident/Capture:** Date the photo/video was originally taken. *If unknown, record "Unknown"*.
*   **Source:** Name/Organization submitting the evidence (e.g., "Policyholder John Doe," "Investigator Jane Smith," "Third-Party Witness").
*   **Description:** A brief, clear summary of what the photo/video depicts (e.g., "Damage to front bumper, driver's side," "Flooded basement, general view," "Exterior view of property before fire").
*   **Number of Files:** Total count of individual photos or video clips.
*   **File Formats:** (e.g., JPEG, MP4).
*   **Location of Incident (if applicable):** Specific address or coordinates if embedded in metadata or provided.
*   **Original File Name(s):** Retain the original file names provided by the submitter.

### 6.3. Uploading to Evidence Management System (EMS)

1.  **Access EMS:** Log in to the designated Evidence Management System using your secure credentials.
2.  **Navigate to Claim:** Locate the specific Claim ID within the EMS.
3.  **Create Evidence Record:** Initiate a new evidence record for the visual media.
4.  **Upload Files:** Use the system's upload function to transfer all relevant photo and video files.
    *   *Requirement:* Each individual image and video clip must be uploaded separately, even if submitted as a compressed archive (e.g., .zip).
5.  **Automated Metadata Extraction:** The EMS will automatically extract standard metadata (e.g., file size, creation date, geolocation if present) and generate a digital fingerprint (hash value) for each file. Verify that this information is recorded.
6.  **Manual Metadata Entry:** Input the required documentation details as outlined in Section 6.2.
7.  **Finalize Upload:** Confirm the upload and ensure all files are correctly associated with the Claim ID.
8.  **Confirmation:** The EMS will generate a unique evidence item ID for each uploaded file or set of related files. Record this ID.

### 6.4. File Naming Convention within EMS

All uploaded files within the EMS will be automatically renamed by the system using a standardized convention to ensure uniqueness and traceability. The convention is:

`[ClaimID]_[EvidenceTypeAbbreviation]_[DateOfIncidentYYYYMMDD]_[SequentialNumber].[OriginalExtension]`

*   **Example for Photo:** `C1234567_PH_20231025_001.jpg`
*   **Example for Video:** `C1234567_VID_20231024_001.mp4`

### 6.5. Access Control and Security

*   **Role-Based Access:** Access to visual evidence within the EMS is strictly controlled via role-based permissions. Only personnel actively assigned to a claim or with explicit authorization will have access.
*   **Audit Trails:** All access, viewing, modification, and download activities within the EMS are logged and auditable.
*   **Encryption:** All data stored in the EMS is encrypted at rest and in transit.
*   **Backup:** A daily backup of the EMS and its contents is performed and stored offsite.

### 6.6. Evidence Preservation and Integrity

*   **Read-Only Storage:** Once uploaded, the original files are stored in a read-only state. Any modifications must be saved as new versions, with a clear audit trail linking to the original.
*   **Digital Fingerprinting:** The automated generation and verification of hash values upon upload and any subsequent access maintain the verifiable integrity of the evidence.
*   **Secure Deletion:** Evidence can only be deleted from the system after the claim lifecycle is complete, litigation holds are lifted, and data retention policies permit, following a secure deletion protocol.

## 7. Evidence Retrieval

1.  **Search Functionality:** Users can retrieve evidence using the Claim ID, Evidence Item ID, submission date range, date of incident, source, or keywords from the description.
2.  **Viewing:** Evidence can be viewed directly within the EMS without needing to download.
3.  **Downloading:** If a download is required (e.g., for legal proceedings, expert review), the activity is logged. The downloaded file will be watermarked with "FOR EXTERNAL USE: [ClaimID] [DownloadDate]" to indicate it's a copy.

## 8. Retention and Archiving

*   **Retention Period:** Photo and video evidence will be retained for a minimum of 7 years from the claim closure date, or longer if mandated by specific state regulations or ongoing litigation.
*   **Archiving:** After the active retention period, evidence will be moved to a secure, long-term archive. Access to archived data requires special authorization.
*   **Destruction:** Following the expiry of all retention periods, evidence will be securely and permanently deleted from all systems and backups.

## 9. Exceptions

*   **Large Files/Bulk Submissions:** For files exceeding 10GB or extremely large volumes (e.g., 500+ photos), consult with the Data Management Team for alternative secure transfer methods (e.g., secure FTP, dedicated transfer appliance) to avoid system performance issues. All subsequent documentation and storage rules still apply.
*   **Corrupted Files:** If evidence is received corrupted and cannot be opened, attempts must be made to contact the submitter for a replacement. If a replacement cannot be obtained, a record of the corrupted file and the attempt to resolve the issue must be logged against the claim.
*   **Sensitive/Redacted Information:** If visual evidence contains sensitive personal information (e.g., faces of minors, private medical records in the background unintentionally captured), adjusters must inform their supervisor. Redaction may be required prior to broader internal sharing or external distribution, following guidelines in the "Data Privacy and Redaction Policy." Any redacted version must be stored as a new version, clearly labeled "Redacted."

## 10. Training

All personnel handling photo and video evidence must complete mandatory training on this SOP and the use of the Evidence Management System annually. New hires involved in claims processing must complete this training within 30 days of their start date.
```
