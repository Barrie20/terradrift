# TerraDrift Candidate Register Data Dictionary

This document defines all fields in `data/pilot/repository_candidates.csv`.

| Field name | Description | Data type | Allowed values | Example | Required | Verification |
|---|---|---|---|---|---|---|
| `candidate_id` | Stable candidate identifier assigned during screening. | string | `CAND-001` format (`CAND-` + three digits), unique per row. | `CAND-001` | Yes | Confirm format and uniqueness with CSV validation checks. |
| `repository_name` | Candidate repository name placeholder until reviewed. | string | Blank before review; otherwise repository short name. | `` | Yes | Compare to source record when review is performed. |
| `repository_url` | Candidate repository URL placeholder until reviewed. | string (URL) | Blank before review; otherwise valid HTTPS repository URL. | `` | Yes | Validate URL syntax and match against reviewed source. |
| `discovery_query` | Query string used to discover candidate. | string | Blank before review or documented query text. | `` | Yes | Confirm query is recorded before candidate selection. |
| `discovery_date` | Date candidate was discovered. | date string | Blank before review or `YYYY-MM-DD`. | `` | Yes | Check date format and consistency with collection notes. |
| `public_repository` | Whether repository is publicly accessible. | categorical | `yes`, `no`, `unknown`. | `unknown` | Yes | Verify from repository accessibility at screening time. |
| `contains_terraform` | Whether repository contains Terraform configuration. | categorical | `yes`, `no`, `unknown`. | `unknown` | Yes | Verify from file inspection during screening. |
| `terraform_file_count` | Count of Terraform files in screening scope. | integer | Blank before review or non-negative integer. | `` | Yes | Recompute using deterministic file-count method. |
| `relevant_commit_count` | Count of commits meeting relevant Terraform commit definition. | integer | Blank before review or non-negative integer. | `` | Yes | Recompute from commit-history extraction process. |
| `default_branch` | Repository default branch at review time. | categorical | Branch name string or `unknown` before review. | `unknown` | Yes | Verify from repository metadata snapshot. |
| `repository_license` | Repository license classification at review time. | categorical | SPDX identifier, `none`, or `unknown`. | `unknown` | Yes | Verify from repository license metadata and LICENSE file if present. |
| `is_fork` | Whether repository is a fork. | categorical | `yes`, `no`, `unknown`. | `unknown` | Yes | Verify from repository metadata during screening. |
| `is_archived` | Whether repository is archived. | categorical | `yes`, `no`, `unknown`. | `unknown` | Yes | Verify from repository metadata during screening. |
| `is_tutorial_or_example` | Whether repository is tutorial/example-only content. | categorical | `yes`, `no`, `unknown`. | `unknown` | Yes | Verify from repository description and content inspection. |
| `sensitive_data_observed` | Whether potential sensitive data was observed during screening. | categorical | `yes`, `no`, `unknown`. | `unknown` | Yes | Verify using documented sensitive-information handling procedure. |
| `eligible_for_pilot` | Pilot eligibility decision after screening. | categorical | `yes`, `no`, `unknown`. | `unknown` | Yes | Verify against inclusion/exclusion criteria and recorded rationale. |
| `exclusion_reason` | Rationale when `eligible_for_pilot` is `no` or unresolved. | string | `unknown` before review or concise reason text. | `unknown` | Yes | Confirm reason aligns with exclusion criteria and review notes. |
| `review_status` | Current review state of candidate row. | categorical | `pending`, `reviewed`. | `pending` | Yes | Verify workflow state transitions in review logs. |
| `reviewer` | Person responsible for row review state. | string | Reviewer name text. | `Alpha Yerroh Barrie` | Yes | Verify against assigned reviewer for pilot screening. |
| `notes` | Free-text implementation notes for screening decisions. | string | Blank or non-sensitive note text. | `` | No | Ensure notes do not include secrets and support reproducibility. |
