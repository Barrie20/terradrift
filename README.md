<div align="center">

# TerraDrift

### Measuring the Persistence and Recurrence of Security Misconfigurations in Public Terraform Repositories

[![CI](https://github.com/Barrie20/terradrift/actions/workflows/ci.yml/badge.svg)](https://github.com/Barrie20/terradrift/actions/workflows/ci.yml)
[![Security](https://github.com/Barrie20/terradrift/actions/workflows/security.yml/badge.svg)](https://github.com/Barrie20/terradrift/actions/workflows/security.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)

**An open and reproducible research project investigating security drift in Infrastructure as Code.**

</div>

---

## Project Status

TerraDrift is an **active research prototype**. It is not yet a peer-reviewed publication, completed large-scale study, or production security product.

### Current status

| Research Component | Status |
|---|---|
| Research-question development | In progress |
| Research methodology | In progress |
| Scanner integration | In progress |
| Pilot repository collection | In progress |
| Pilot security analysis | In progress |
| Manual validation | Planned |
| Large-scale corpus analysis | Planned |
| Public dataset release | Planned |
| Faculty or independent review | Not yet established |
| Peer-reviewed submission | Not yet submitted |
| External adoption | Not yet established |

All project results will be reported only after the relevant experiments have been completed and validated.

---

## Overview

Infrastructure as Code, or IaC, allows organizations to define and deploy cloud infrastructure using version-controlled configuration files.

Terraform is one of the most widely used Infrastructure-as-Code technologies. Although Terraform improves repeatability and automation, its configuration files may contain security misconfigurations such as:

- Publicly accessible storage
- Overly permissive network rules
- Missing encryption settings
- Weak identity and access controls
- Insufficient logging or monitoring
- Insecure default configurations
- Hard-coded secrets
- Unrestricted ingress or egress
- Misconfigured cloud resources

Existing security scanners can identify many of these issues. However, identifying a finding at one point in time does not explain:

- How long the finding remains in the repository
- Whether the finding is eventually corrected
- Whether the same finding later returns
- Whether different scanners agree
- Whether repository characteristics affect remediation
- Whether scanner findings represent valid security concerns or false positives

TerraDrift is being developed to study these questions using public Terraform repositories and reproducible empirical methods.

---

## Central Research Question

> How long do identifiable security misconfigurations persist in public Terraform repositories, and how frequently do previously corrected misconfigurations recur?

---

## Research Questions

### RQ1: Persistence

How long do security scanner findings remain present in public Terraform repositories?

### RQ2: Remediation

What proportion of identified findings are eventually corrected?

### RQ3: Recurrence

How often do findings reappear after they appear to have been corrected?

### RQ4: Misconfiguration categories

Which categories of security findings persist the longest or recur most frequently?

### RQ5: Scanner agreement

How consistently do different Infrastructure-as-Code security scanners identify the same or similar findings?

### RQ6: Repository characteristics

Are repository characteristics associated with faster or slower remediation?

Potential characteristics may include:

- Repository age
- Repository activity
- Number of contributors
- Commit frequency
- Project size
- Presence of automated security workflows
- Presence of dependency or security policies

### RQ7: False positives

What proportion of sampled scanner findings cannot be confirmed through manual validation?

---

## Intended Contributions

If completed successfully, TerraDrift is intended to contribute:

1. A reproducible pipeline for analyzing security findings across Terraform repository histories.
2. A documented method for measuring finding persistence, remediation, and recurrence.
3. A research dataset derived from eligible public repositories.
4. A comparison of selected Infrastructure-as-Code security scanners.
5. An analysis of common threats to validity in longitudinal IaC-security research.
6. Practical recommendations for developers, researchers, and DevSecOps teams.
7. Open-source code and documentation that may support replication or extension.

These are intended contributions. They should not be interpreted as completed results until corresponding releases and evidence are published.

---

## Definitions

For this project, the following working definitions are used.

### Security finding

A security-related result produced by a supported Infrastructure-as-Code scanner.

A scanner finding is not automatically treated as proof of an exploitable vulnerability.

### Persistence

The observed period during which a normalized security finding remains detectable across selected repository revisions.

### Remediation

The apparent removal or correction of a previously detected finding.

### Recurrence

The reappearance of a normalized finding after it was previously classified as remediated.

### Security drift

A measurable change in the security posture of Infrastructure-as-Code files over time, including the introduction, persistence, remediation, or recurrence of security findings.

These definitions may be refined as the research methodology develops.

---

## Important Interpretation Limitation

TerraDrift analyzes source-code repositories and scanner outputs.

A finding in a public Terraform repository does **not** necessarily prove that:

- The configuration was deployed
- The associated cloud resource currently exists
- A production environment is vulnerable
- A specific organization suffered a security incident
- The scanner finding is a true positive
- The repository owner ignored a known security issue

Results must therefore be interpreted carefully and validated before drawing conclusions.

---

## Planned Research Design

The project is being developed in phases.

### Phase 1: Research design

- Define the research questions
- Define inclusion and exclusion criteria
- Review related literature
- Select security scanners
- Define finding-normalization rules
- Establish ethical data-handling practices
- Identify threats to validity

### Phase 2: Small pilot

- Select a small set of eligible public repositories
- Validate repository-mining procedures
- Test scanner execution
- Evaluate storage requirements
- Measure execution time and cost
- Identify duplicate and unstable findings
- Manually inspect a sample of results

### Phase 3: Expanded pilot

- Analyze approximately 50–100 eligible repositories
- Refine finding normalization
- Compare scanner agreement
- Develop persistence and recurrence measures
- Estimate false-positive rates
- Document methodology changes

### Phase 4: Larger empirical study



Subject to successful pilot validation and available resources, the project may expand to a larger public-repository corpus.

The final corpus size will depend on:

- Repository eligibility
- License and usage considerations
- Availability of Terraform commit history
- Computational resources
- API limits
- Scanner performance
- Data quality
- Research-review feedback

No proposed corpus size should be interpreted as a completed result.

### Phase 5: Reproducibility and publication

- Freeze tool versions
- Publish the final methodology
- Document inclusion and exclusion criteria
- Release non-sensitive derived data where permitted
- Archive a versioned software release
- Prepare a replication guide
- Seek faculty or independent review
- Consider submission to a legitimate research venue

---

## Proposed Repository Eligibility Criteria

A repository may be considered for analysis if it:

- Is publicly accessible
- Contains Terraform configuration files
- Has sufficient version history for longitudinal analysis
- Can be accessed within applicable platform rules
- Does not require bypassing authentication or access controls
- Has enough technical information to support reproducible analysis
- Falls within the final documented sampling methodology

A repository may be excluded if it:

- Is a duplicate or mirror
- Contains only tutorial fragments
- Contains generated files without meaningful history
- Has insufficient commit history
- Cannot be processed reliably
- Presents unresolved legal, ethical, or licensing concerns
- Contains sensitive information that should not be included in the research dataset

The final eligibility criteria will be documented before reporting full-study results.

---

## Proposed Technical Workflow

```text
Public Repository Discovery
            |
            v
Eligibility and Deduplication
            |
            v
Repository Metadata Collection
            |
            v
Terraform File Identification
            |
            v
Commit and Revision Selection
            |
            v
Security Scanner Execution
            |
            v
Finding Normalization
            |
            v
Persistence and Recurrence Analysis
            |
            v
Manual Validation Sample
            |
            v
Statistical Analysis
            |
            v
Reproducible Dataset and Report
