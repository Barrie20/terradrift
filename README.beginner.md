# TerraDrift — Beginner's Guide

> Welcome. If you're new to cloud security, this page is for you.

## What is "Infrastructure as Code"?

Imagine you used to set up your house by walking around and plugging in furniture by hand. Slow, error-prone, and impossible to redo for a friend's house.

**Infrastructure as Code (IaC)** is like writing a recipe for your house. You write a file that says "two bedrooms, one kitchen, a router by the window," and a tool builds it for you, the same way every time. **Terraform** is the most popular tool for writing those recipes for cloud infrastructure (AWS, Google Cloud, Azure).

## What is a "misconfiguration"?

A misconfiguration is a mistake in the recipe.

**Real-world examples:**

| Recipe mistake | Real-world consequence |
|---|---|
| Forgetting to lock the front door | An S3 bucket left public — like the 2017 Verizon leak that exposed 14 million records |
| Leaving spare keys under the mat | Hard-coded AWS access keys in a Terraform file — like the 2019 Capital One breach |
| Not setting an alarm | No CloudTrail logging — you can't tell when someone broke in |

## What is "drift"?

Drift is when the recipe **starts correct, then slowly goes wrong** over time. Like a healthy diet that drifts into pizza every night.

**Real-world example:** A team writes a perfect Terraform module on Day 1. Six months later, an engineer adds a quick fix at 11 PM, accidentally making a database publicly accessible. Nobody notices for 200 days. That's drift.

## What does TerraDrift do?

TerraDrift looks at thousands of public Terraform recipes on GitHub and answers:
- How often do people make these mistakes?
- How long until someone notices?
- Do mistakes come back after being fixed? (Yes, surprisingly often.)

## Try it yourself in 5 minutes

```bash
# 1. Get the code
git clone https://github.com/Barrie20/terradrift.git
cd terradrift

# 2. Run the demo
make demo
```

You'll see a report like this:

```
🔍 Scanning sample/aws-s3-public/
   ✗ CKV_AWS_18  S3 bucket has no access logging
   ✗ CKV_AWS_53  S3 bucket allows public read
   ✓ CKV_AWS_145 KMS encryption enabled
3 checks, 2 failures, 1 pass — see report.csv
```

## What do I do next?

1. Read [`README.research.md`](README.research.md) if you're curious about the science.
2. Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) if you want to know how it's built.
3. Open an issue if anything is unclear — we'll explain it.

## Glossary

- **Terraform** — a tool that builds cloud infrastructure from a config file.
- **Module** — a reusable Terraform recipe (like a function in code).
- **Checkov / Trivy / tfsec** — robots that read Terraform files and yell when they find mistakes.
- **CWE** — Common Weakness Enumeration; an industry list of mistake types.
- **Drift** — the slow degradation of correct configuration over time.
