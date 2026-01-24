```markdown
---
title: Policy Document Templates and Samples
type: reference
tags: [policy, template, samples, documentation, insurance, underwriting, claims, reference]
effective_date: 2023-10-26
---

# Policy Document Templates and Samples

## Overview
This document serves as a central repository for blank and populated policy document templates across various insurance products offered by StellarProtect. Its primary purpose is to standardize policy creation, ensure consistency in coverage terms and conditions, and provide readily accessible samples for reference, training, and claim adjudication. This resource is critical for underwriters, claims adjusters, legal teams, and customer service representatives to ensure accurate policy interpretation and application.

## Scope
This document covers:
*   Standard templates for primary StellarProtect insurance products (e.g., Auto, Home, Life, Business Liability).
*   Templates for common endorsements, riders, and addendums.
*   Examples of successfully issued policies demonstrating correct template usage and variable data population.
*   Guidelines for accessing and utilizing these templates.

This document does *not* cover:
*   Specific underwriting guidelines for risk assessment (refer to "Underwriting Manuals").
*   Claim processing procedures (refer to "Claims Processing SOPs").
*   Legal interpretations of specific clauses unless explicitly stated as an example.

## Definitions
*   **Policy Document:** The formal legal contract outlining the terms, conditions, coverage, exclusions, and limits of an insurance agreement between StellarProtect and the policyholder.
*   **Template:** A pre-formatted document structure with placeholder text (`[FIELD_NAME]`) designed for repeatable use, ensuring consistency across similar policy types.
*   **Sample Policy:** A fully populated policy document that has been issued to a policyholder, serving as a live example of a completed policy.
*   **Endorsement/Rider:** An amendment or addition to a standard insurance policy that alters its terms, scope, or coverage.
*   **P&C:** Property & Casualty insurance.
*   **L&H:** Life & Health insurance.

## Policy Document Templates
All templates are maintained in the StellarProtect Document Management System (DMS) under the path `/DMS/PolicyTemplates/`. Access requires appropriate departmental permissions.

### 1. Auto Insurance Policy Templates
*   **Template Name:** AutoPolicy_Standard_V3.1.docx
    *   **Description:** Comprehensive standard auto policy template.
    *   **Key Sections:** Declarations Page, Definitions, Covered Autos, Covered Persons, Liability Coverage (Bodily Injury, Property Damage), Collision Coverage, Comprehensive Coverage, Medical Payments/Personal Injury Protection (PIP), Uninsured/Underinsured Motorist, General Policy Provisions, Exclusions.
    *   **Required Variables:** `[POLICY_NUMBER]`, `[EFFECTIVE_DATE]`, `[EXPIRATION_DATE]`, `[POLICYHOLDER_NAME]`, `[ADDRESS]`, `[VEHICLE_YEAR_MAKE_MODEL_VIN]`, `[COVERAGE_LIMITS_BI_PD_COLL_COMP_PIP_UMUIM]`, `[PREMIUM_AMOUNT]`, `[DEDUCTIBLES]`.
*   **Template Name:** AutoPolicy_Commercial_Fleet_V1.2.docx
    *   **Description:** Template for commercial fleet auto insurance policies.
    *   **Specifics:** Includes sections for fleet schedules, commercial use endorsements, driver lists, and higher liability limits.
*   **Sample Reference:** `AutoPolicy_Sample_SPD7890123_2023-01-15_JohnDoe.pdf`

### 2. Homeowners Insurance Policy Templates
*   **Template Name:** HomeownerPolicy_StandardHO3_V4.0.docx
    *   **Description:** Standard HO-3 (special form) policy template for owner-occupied dwellings.
    *   **Key Sections:** Declarations Page, Dwelling Coverage (Coverage A), Other Structures (Coverage B), Personal Property (Coverage C), Loss of Use (Coverage D), Personal Liability (Coverage E), Medical Payments to Others (Coverage F), Perils Insured Against, General Exclusions, Conditions.
    *   **Required Variables:** `[POLICY_NUMBER]`, `[EFFECTIVE_DATE]`, `[EXPIRATION_DATE]`, `[POLICYHOLDER_NAME]`, `[PROPERTY_ADDRESS]`, `[DWELLING_REPLACEMENT_COST]`, `[COVERAGE_LIMITS_A_B_C_D_E_F]`, `[DEDUCTIBLES]`, `[PREMIUM_AMOUNT]`.
*   **Template Name:** HomeownerPolicy_RenterHO4_V2.1.docx
    *   **Description:** Template for HO-4 (renters insurance) policies.
    *   **Specifics:** Focuses on personal property, loss of use, and liability; excludes dwelling coverage.
*   **Sample Reference:** `HomePolicy_Sample_HPL1122334_2023-03-01_JaneSmith.pdf`

### 3. Life Insurance Policy Templates
*   **Template Name:** LifePolicy_TermLife_V2.0.docx
    *   **Description:** Template for Level Term Life insurance policies.
    *   **Key Sections:** Declarations Page, Insured Information, Beneficiary Designation, Policy Description, Coverage Amount, Term Duration, Premium Schedule, Policy Loans, Cash Surrender Value (if applicable), General Provisions, Exclusions, Application as Part of Policy.
    *   **Required Variables:** `[POLICY_NUMBER]`, `[ISSUE_DATE]`, `[INSURED_NAME_DOB]`, `[BENEFICIARY_NAME_RELATION_SHARE]`, `[DEATH_BENEFIT_AMOUNT]`, `[TERM_DURATION_YEARS]`, `[PREMIUM_AMOUNT_FREQUENCY]`.
*   **Template Name:** LifePolicy_WholeLife_V1.5.docx
    *   **Description:** Template for Whole Life insurance policies.
    *   **Specifics:** Includes sections on guaranteed cash value accumulation, non-forfeiture options, and dividends.
*   **Sample Reference:** `LifePolicy_Sample_LFE9988776_2022-11-01_RobertJohnson.pdf`

### 4. Business Liability Policy Templates
*   **Template Name:** BusinessLiability_General_V3.0.docx
    *   **Description:** Template for Commercial General Liability (CGL) policies.
    *   **Key Sections:** Declarations Page, Insured Organization Details, Coverage Territory, Coverage A (Bodily Injury & Property Damage), Coverage B (Personal & Advertising Injury), Coverage C (Medical Payments), Limits of Insurance, Conditions, Definitions, Exclusions.
    *   **Required Variables:** `[POLICY_NUMBER]`, `[EFFECTIVE_DATE]`, `[EXPIRATION_DATE]`, `[INSURED_ORGANIZATION_NAME]`, `[BUSINESS_ADDRESS]`, `[BUSINESS_ACTIVITY_NAICS]`, `[AGGREGATE_LIMITS]`, `[OCCURRENCE_LIMITS]`, `[PREMIUM_AMOUNT]`.
*   **Sample Reference:** `BizLiabPolicy_Sample_CGL4567890_2023-06-15_AcmeCorp.pdf`

### 5. Common Endorsements/Riders Templates
*   **Template Name:** Endorsement_ScheduledPersonalProperty_V1.0.docx
    *   **Applicable To:** Homeowners
    *   **Purpose:** To add specific high-value items (e.g., jewelry, art, furs) to a homeowners policy with their own coverage limits and often lower deductibles.
    *   **Required Variables:** `[POLICY_NUMBER]`, `[ENDORSEMENT_DATE]`, `[ITEM_DESCRIPTION]`, `[APPRAISED_VALUE]`, `[DEDICATED_LIMIT]`.
*   **Template Name:** Rider_WaiverOfPremium_Life_V1.1.docx
    *   **Applicable To:** Life Insurance
    *   **Purpose:** Waives premium payments if the insured becomes totally and permanently disabled.
    *   **Required Variables:** `[POLICY_NUMBER]`, `[RIDER_EFFECTIVE_DATE]`, `[ADDITIONAL_PREMIUM_WAIVER]`.
*   **Template Name:** Endorsement_NamedDriverExclusion_Auto_V1.0.docx
    *   **Applicable To:** Auto Insurance
    *   **Purpose:** Excludes a specific individual from coverage under the auto policy, typically due to high-risk driving history.
    *   **Required Variables:** `[POLICY_NUMBER]`, `[ENDORSEMENT_DATE]`, `[EXCLUDED_DRIVER_NAME_DOB_LICENSE]`.

## Access and Utilization Procedures
1.  **Accessing Templates:**
    *   All blank templates are located in the StellarProtect DMS (`/DMS/PolicyTemplates/`).
    *   All sample policies are located in the DMS (`/DMS/PolicySamples/`).
    *   Users require read/write access for templates (underwriters) and read-only access for samples (claims, CS).
2.  **Creating a New Policy (Underwriters):**
    *   Download the appropriate blank template (e.g., `AutoPolicy_Standard_V3.1.docx`).
    *   **DO NOT** modify the template structure or boilerplate legal text.
    *   Populate all `[FIELD_NAME]` variables with accurate policyholder and coverage information derived from the application and underwriting decisions.
    *   Ensure all necessary endorsements or riders are appended using their respective templates.
    *   Save the completed policy as a PDF using the standardized naming convention: `[PolicyType]_SPD[PolicyNumber]_[IssueDate_YYYY-MM-DD]_[PolicyholderName].pdf` (e.g., `AutoPolicy_SPD7890123_2023-01-15_JohnDoe.pdf`).
    *   Upload the final PDF to the policyholder's digital file in the Claims & Policy Management System (CPMS) and the DMS.
3.  **Referencing Policies (Claims Adjusters, CS):**
    *   When reviewing a claim or customer inquiry, navigate to the policyholder's record in CPMS.
    *   Locate the "Policy Documents" section to find the issued policy PDF.
    *   If a specific clause or coverage type needs clarification, refer to the relevant blank template to understand the default language prior to any policy-specific modifications via endorsements.
    *   For training purposes or general reference, use the `PolicySamples` folder in the DMS.

## Exceptions
*   **Custom Commercial Policies:** For highly bespoke commercial policies (e.g., specialized marine cargo, bespoke professional liability), standard templates may serve as a baseline, but significant customization by legal and underwriting teams will be required. These custom policies must undergo enhanced legal review and approval.
*   **Legacy Products:** Policies issued under older product lines (pre-2015) may use previous template versions. These older templates are archived in `/DMS/PolicyTemplates/Archive/` and should be referenced if claims pertain to policies issued under those legacy forms, specifically for policies issued before `2015-01-01`.

## Documentation Requirements
*   All issued policies must have a digitally signed or recorded acceptance by the policyholder.
*   Any deviations from standard template language, even minor ones for custom policies, must be explicitly documented in the underwriting file and approved by a Senior Underwriter or Legal Counsel.
*   Policy documents and all related endorsements must be archived electronically for a minimum of `10 years` after the policy's expiration or termination date.

## Timelines
*   New product templates or significant template revisions are typically reviewed quarterly and updated by `January 15th`, `April 15th`, `July 15th`, and `October 15th` each year.
*   Emergency template updates (e.g., due to regulatory changes) are implemented within `5 business days` of the directive.
*   Underwriters are expected to use the most current template version available in the DMS at the time of policy issuance unless a specific effective date for a new version is declared.
```
