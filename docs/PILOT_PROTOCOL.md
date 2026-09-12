# TerraDrift Pilot Research Protocol

- **Protocol version:** 0.1
- **Date established:** September 2026
- **Researcher:** Alpha Yerroh Barrie
- **Pilot target:** 10 eligible public Terraform repositories

## Purpose and feasibility objectives

This pilot establishes and tests a reproducible workflow for studying the persistence and recurrence of Terraform security scanner findings over repository history. Feasibility objectives include validating repository selection workflow, scanner execution repeatability, finding normalization, and manual verification procedures before any larger study.

## Sampling statement

The pilot uses a convenience sample of public repositories and is not statistically representative of the full Terraform ecosystem.

## Primary unit of analysis

The primary unit of analysis is a normalized Terraform finding identity observed at a specific repository revision.

## Primary pilot research questions

1. Can at least 10 eligible public Terraform repositories be selected using a documented and reproducible process?
2. Can Checkov and Trivy be run consistently on selected repository revisions?
3. Can finding identities be normalized and tracked across revisions for persistence, apparent remediation, and recurrence?
4. What practical data-quality and workflow constraints appear during pilot execution?
5. Can at least 20 findings be manually reviewed under this protocol?

## Repository-discovery procedure

1. Define and record discovery queries before candidate review.
2. Record each discovered candidate in `data/pilot/repository_candidates.csv`.
3. Evaluate each candidate against inclusion and exclusion criteria.
4. Keep screening fields and justifications in the candidate register.
5. Do not modify selection rules after reviewing scanner outputs.

## Candidate-evaluation requirement

At least 20 candidate repositories must be evaluated and documented in the candidate register before selecting the final pilot sample.

## Inclusion criteria

A candidate repository is eligible only if it is public, contains Terraform configuration, has reviewable commit history, and can be analyzed without bypassing access controls.

## Exclusion criteria

Exclude repositories that are archived, forks with no independent Terraform history, tutorial/example-only material, non-actionable Terraform content, or repositories requiring prohibited handling of sensitive information.

## Deterministic selection rule

After screening, order eligible candidates by ascending `candidate_id` and select the first 10 eligible entries. Candidates must not be selected because they appear likely to produce more findings. A selected repository cannot be replaced merely because it produces no findings.

## Definitions

### Relevant Terraform commit

A relevant Terraform commit is a commit that adds, deletes, or modifies Terraform configuration files or modules included in scanner scope.

### Finding identity

A finding identity is a deterministic key formed from scanner name, normalized rule identifier, file path, and normalized resource/address context.

### Persistence

Persistence is the count or span of analyzed revisions in which the same finding identity remains present.

### Apparent remediation

Apparent remediation is the first analyzed revision where a previously present finding identity is no longer detected.

### Recurrence

Recurrence is the reappearance of a previously remediated finding identity in a later analyzed revision.

### Uncertain classification

A finding is classified as uncertain when available repository evidence is insufficient to determine whether scanner output reflects a materially actionable misconfiguration.

## Scanner selection

The pilot scanner set is Checkov and Trivy.

## Data handling and validation

- Raw scanner output and normalized analytical data must be stored separately.
- At least 20 findings must undergo manual validation and documented outcomes.
- Failed analyses must be documented, including repository, revision, failure mode, and recovery or exclusion decision.

## Sensitive-information procedure

Credentials or other sensitive data must not be copied, tested, executed, or redistributed. If sensitive material is observed, record only minimal non-secret metadata needed for exclusion or handling decisions.

## Responsible interpretation

- Scanner findings are not proof of deployed vulnerabilities.
- Repository configurations may never have been deployed.
- Public repositories are not representative of private enterprise systems.
- Repository owners must not be accused of security failures based solely on static-analysis findings.

## Required pilot outputs

1. Candidate register with at least 20 evaluated entries.
2. Final list of 10 selected repositories with eligibility rationale.
3. Versioned raw scanner outputs.
4. Normalized finding dataset and transformation rules.
5. Manual-validation sample log for at least 20 findings.
6. Pilot summary documenting limitations and next-step recommendations.

## Success criteria

The pilot is successful if repository selection is reproducible, scanner runs complete for the selected sample with documented exceptions, normalization is repeatable, manual validation minimums are met, and limitations are explicitly reported.

## Protocol-amendment procedure

Methodology must not be silently changed after reviewing results. Any change to this protocol requires a dated amendment entry in `docs/PROTOCOL_AMENDMENTS.md` with prior language, updated language, rationale, timing (before or after result review), and approver.

## Current limitations

This protocol is a feasibility plan for a small pilot and does not claim completed experimental results, external adoption, or peer-reviewed conclusions.
