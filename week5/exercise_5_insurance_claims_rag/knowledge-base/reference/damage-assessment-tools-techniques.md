```markdown
---
title: Damage Assessment Tools and Techniques
type: reference
tags:
  - damage assessment
  - claims processing
  - tools
  - techniques
  - inspection
  - digital assessment
  - drone survey
effective_date: 2023-10-26
---

# Damage Assessment Tools and Techniques

## Overview
This document serves as a comprehensive reference guide for claims adjusters, providing detailed information on various tools and techniques utilized in damage assessment. The objective is to standardize assessment methodologies, improve efficiency, enhance accuracy, and ensure consistent application of best practices across all claim types, ultimately leading to fair and timely claim resolutions.

## Scope
This reference applies to all claims adjusters involved in property, auto, and specialized claims requiring physical or digital damage assessment. It covers a range of techniques from traditional on-site inspections to advanced digital and remote assessment methods. Excluded are highly specialized industrial or environmental damage assessments that require specific certifications or regulatory oversight beyond standard property/casualty claims.

## Definitions
*   **Damage Assessment:** The process of evaluating the nature, extent, and cause of damage to insured property or assets.
*   **On-Site Inspection:** Physical visit by an adjuster to the damaged location to survey and document damage.
*   **Desk Adjustment:** Claims handled remotely without a physical on-site visit, often relying on policyholder-provided documentation, photos, and digital tools.
*   **Digital Claim Intake:** The process by which policyholders submit information, photos, or videos of damage electronically.
*   **Geospatial Data:** Information linked to a specific location, often used in conjunction with satellite imagery or drone data.
*   **Thermal Imaging:** A technique using infrared cameras to detect temperature differences, often indicating moisture, energy loss, or structural issues.
*   **Matterport/3D Scan:** Technology that creates a three-dimensional representation of an interior space, allowing for virtual walkthroughs and detailed measurements.

## Main Content: Damage Assessment Techniques

### 1. Traditional On-Site Inspection
The foundational method for damage assessment, involving a physical visit to the loss site.

#### Procedures/Steps:
1.  **Safety First:** Adjuster ensures personal safety and assesses any immediate hazards at the site before commencing inspection.
2.  **Initial Walkthrough:** Conduct a preliminary visual inspection to understand the overall scope of damage.
3.  **Photo/Video Documentation:** Systematically capture high-resolution photos and videos of all damaged areas from multiple angles. Include panoramic shots and close-ups, with clear identifiers (e.g., street numbers, property features).
    *   **Requirements:** Photos must be date/time stamped, geo-tagged, and clearly illustrate pre-damage condition (if available) and post-damage state. Minimum of 5 photos per damaged item/area.
4.  **Measurements:** Accurately measure damaged areas (e.g., roof square footage, wall length, floor area). Use laser distance measurers where appropriate.
5.  **Damage Identification:** Clearly identify the type of damage (e.g., impact, water, fire, wind) and its apparent cause.
6.  **Material Identification:** Document types of materials affected (e.g., roofing shingles, siding, flooring, drywall).
7.  **Symptom/Root Cause Analysis:** Attempt to identify the root cause of the damage based on visible symptoms (e.g., water stains leading to a roof leak).
8.  **Interview Policyholder/Witnesses:** Gather firsthand accounts of the incident and damage.
9.  **Sketching:** Create detailed diagrams or sketches of the affected property layout, noting damaged areas.

### 2. Digital Claim Intake & Photo Analysis
Leveraging policyholder-submitted documentation for initial assessment or desk adjustments.

#### Procedures/Steps:
1.  **Policyholder Guidance:** Provide clear instructions for policyholders on how to capture effective photos and videos using dedicated mobile apps or web portals.
    *   **Requirements:** Instructions should specify requirements for lighting, angle, distance, inclusion of a common object for scale (e.g., ruler, coin), and multi-angle shots.
2.  **AI-Powered Damage Detection:** Utilize integrated AI tools within the claims platform to analyze submitted photos for common damage types (e.g., hail dings on vehicles, roof damage).
    *   **Decision Logic:** If AI confidence score > 85% for identified damage type, adjuster greenlights for desk review. If score < 85% or unclear, flag for manual review or potential on-site inspection.
3.  **Manual Photo Review:** Adjuster meticulously reviews all submitted media, cross-referencing against policy details and claim narrative.
4.  **Virtual Measurement Tools:** Employ software that can estimate dimensions from photos using known objects or AI algorithms.
    *   **Accuracy Threshold:** Measurements derived from photo analysis must fall within a 10% variance of expected values to be considered reliable for desk adjustment. Outside this range requires additional verification.

### 3. Drone & Aerial Imagery
Utilizing unmanned aerial vehicles (UAVs) or satellite imagery for large-area or high-risk assessments.

#### Applicability:
*   **Large-scale disasters:** Hurricanes, widespread hail events, wildfires.
*   **High roofs/inaccessible areas:** Multi-story buildings, steep pitches, dangerous environments.
*   **Commercial properties:** Complex roof structures, large footprints.

#### Procedures/Steps:
1.  **Flight Planning (for Drones):** Obtain necessary airspace authorizations (e.g., FAA Part 107 compliance for commercial operations). Define flight path, altitude, and camera angles.
2.  **High-Resolution Capture:** Drones capture high-definition photos (minimum 20MP) and 4K video, often with orthogonal (straight-down) views and oblique (angled) perspectives.
3.  **Imagery Processing:** Raw drone data is processed using specialized software to create high-resolution orthomosaic maps, 3D models, and digital elevation models (DEMs).
4.  **Damage Annotation:** Adjusters or specialized analysts review processed imagery to identify, measure, and annotate damaged areas directly on the maps/models.
    *   **Tools:** Integrated annotation tools allow for marking specific damage types (e.g., missing shingles, impact areas, water lines).
5.  **Wind/Hail Analysis:** Specific algorithms can analyze roof shingle granules, uplift patterns, and impact craters from drone imagery to distinguish between wind and hail damage effectively.

### 4. Thermal Imaging
Detecting moisture, electrical faults, and insulation deficiencies.

#### Applicability:
*   Hidden water leaks (e.g., behind walls, under flooring).
*   Mold assessment (due to moisture).
*   Electrical system overheating.
*   Building envelope issues (e.g., poor insulation, air leaks leading to energy loss).

#### Procedures/Steps:
1.  **Equipment Calibration:** Ensure thermal camera is calibrated for ambient conditions.
2.  **Systematic Scan:** Conduct a systematic scan of affected areas, looking for temperature anomalies.
3.  **Interpretation:** Analyze color gradients and temperature readings on the thermal image.
    *   **Decision Logic:** Significant temperature differentials (typically >3-5°F) compared to surrounding areas often indicate moisture (cooler) or heat sources/losses (warmer). Requires correlation with visual inspection.
4.  **Follow-up:** Thermal imaging often leads to further invasive inspection (e.g., opening drywall) to confirm findings.

### 5. Matterport / 3D Scanning
Creating immersive 3D models for detailed interior documentation and measurement.

#### Applicability:
*   Extensive interior damage (e.g., fire, water, mold).
*   Complex layouts for commercial properties.
*   Content inventory and loss documentation.
*   Virtual re-inspection or collaboration with contractors.

#### Procedures/Steps:
1.  **Scanner Deployment:** Place the Matterport camera (or similar 3D scanner) at regular intervals throughout the damaged property.
2.  **3D Model Generation:** The camera captures spatial data and images, which are then processed into a navigable 3D "digital twin" of the property.
3.  **Virtual Tour & Measurement:** Adjusters can virtually walk through the property, take precise measurements (e.g., wall lengths, ceiling heights, door openings), and identify damaged items.
4.  **Annotation & Report Export:** Mark damaged areas, add notes, and export floor plans or Xactimate-compatible sketches directly from the 3D model.

## Requirements/Criteria for Technique Selection

### Decision Logic for On-Site vs. Desk Adjustment:
*   **Claim Severity:**
    *   **Low Severity (Est. <$5,000):** Prioritize Desk Adjustment using digital intake and photo analysis.
    *   **Medium Severity (Est. $5,000 - $25,000):** Initial Desk Adjustment, may escalate to On-Site if complexity or verification issues arise.
    *   **High Severity (Est. >$25,000):** Mandatory On-Site Inspection, often supplemented by drone/3D scanning.
*   **Damage Complexity:** Simple, obvious damage (e.g., broken window) suitable for desk. Complex or hidden damage (e.g., structural, water intrusion origin) requires on-site.
*   **Policyholder Capability:** Ability/willingness of policyholder to provide clear documentation electronically.
*   **Access Issues:** If property is inaccessible or unsafe, remote methods (drone) are preferred.
*   **Fraud Indicators:** Any red flags require mandatory on-site inspection.

## Evidence/Documentation Requirements

For **all** assessment methods, the following documentation is mandatory:
*   **Claim File Notes:** Detailed narrative of assessment process, findings, and decisions.
*   **Date/Time Stamped Photos/Videos:** High resolution, geo-tagged, clearly depicting damage and context.
*   **Measurements:** Digital or manual, clearly labeled sketches or reports.
*   **Estimates/Scope of Work:** Based on assessment findings.
*   **Third-Party Reports:** If specialists (e.g., engineers, restoration companies) are involved.
*   **Drone Flight Logs/Processed Imagery:** For aerial assessments.
*   **Thermal Images/Readings:** For thermal assessments.
*   **3D Model Link/Exported Data:** For 3D scanning assessments.

## Exceptions
*   **Catastrophic Events:** During widespread catastrophic events, initial damage assessments may be streamlined due to resource constraints. This may involve rapid aerial assessments followed by deferred detailed on-site inspections.
*   **Emergency Services:** Immediate actions to mitigate further damage (e.g., water extraction, tarping) may precede full assessment. Evidence of these actions should be documented retrospectively.
*   **Specialized Claims:** Certain claims (e.g., high-value art, industrial machinery) may require independent experts or specialized tools not detailed in this general reference.

## Examples

### Example 1: Hail Damage to Residential Roof
*   **Initial Assessment:** Policyholder submits photos via mobile app. AI tool detects potential hail impact.
*   **Decision:** Due to roof height/pitch and potential for widespread damage, desk adjuster orders a drone inspection.
*   **Adjuster Action:** Drone operator captures orthomosaic map and high-res images. Adjuster uses software to identify 200+ hail impacts on shingles and assess slope, size of roof. Uses this data to generate an Xactimate estimate.

### Example 2: Water Leak in a Multi-Unit Building
*   **Initial Assessment:** Policyholder reports water stains on ceiling.
*   **Decision:** Adjuster performs an on-site inspection. Visual assessment and moisture meter detect elevated moisture.
*   **Adjuster Action:** Adjuster utilizes a thermal camera to trace the source of the water within the ceiling and wall cavities, pinpointing a burst pipe behind a specific wall section. This avoids extensive unnecessary demolition.

### Example 3: Commercial Property Fire Damage
*   **Initial Assessment:** Significant fire damage reported.
*   **Decision:** Mandatory on-site inspection with 3D scanning.
*   **Adjuster Action:** Adjuster, accompanied by a structural engineer, conducts an on-site inspection. A Matterport scan is performed to create a detailed digital twin of the damaged interior, facilitating precise measurements for demolition, restoration, and content inventory, and aiding contractors in bidding and planning.
```
