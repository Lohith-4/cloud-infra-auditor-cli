# Cloud Infrastructure Auditor & Cost Optimizer (CLI)

A professional-grade CLI tool for DevOps and FinOps teams to audit cloud
infrastructure for orphaned, underutilized, or misconfigured resources,
generate cost-saving reports, and safely clean up waste.

## Status
🚧 Under active development — Week 1, Day 1-2 complete (CLI skeleton).

## Tech Stack
- Python 3.13
- Typer + Rich (CLI framework & formatting)
- Boto3 (AWS SDK)

## Setup
\`\`\`bash
python -m venv venv
venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
\`\`\`

## Usage
\`\`\`bash
python -m auditor.cli --help
python -m auditor.cli scan ebs --region us-east-1
\`\`\`