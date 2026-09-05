# Cloud Infrastructure Auditor & Cost Optimizer (CLI)

A professional-grade Command Line Interface (CLI) tool for DevOps and
FinOps teams. Scans AWS infrastructure for orphaned, underutilized, or
misconfigured resources, generates cost-saving reports, and provides
safe, auditable cleanup commands.

## Features

- **Secure authentication** — supports local AWS named profiles and
  cross-account role assumption via STS
- **Resource scanning:**
  - Unattached EBS volumes
  - Unassociated Elastic IPs
  - Underutilized EC2 instances (sub-threshold CPU over a configurable
    lookback window, via CloudWatch)
- **Cost-aware reporting** — every finding includes an estimated
  monthly cost impact
- **Rich terminal output** — color-coded tables and summary panels
- **Export** — save full audit results to CSV and/or JSON
- **Safe cleanup** — dry-run by default; destructive actions require
  explicit `--execute` plus a typed confirmation phrase
- **Audit logging** — every cleanup action (success or failure) is
  logged with a timestamp
- **Automatic retry** — AWS API throttling is handled with exponential
  backoff and jitter
- **Fully tested** — unit tests use `moto` to mock AWS, so the test
  suite runs with zero AWS cost and no real account required

## Tech Stack

- Python 3.13
- Typer + Rich (CLI framework and terminal formatting)
- Boto3 / Botocore (AWS SDK)
- Moto (AWS mocking for tests)
- PyInstaller + Setuptools (packaging)

## Installation

### From source (development)

```bash
git clone https://github.com/Lohith-4/cloud-infra-auditor-cli.git
cd cloud-infra-auditor-cli
python -m venv venv
venv\Scripts\Activate.ps1      # Windows
pip install -r requirements.txt
pip install -e .
```

### Standalone executable

Download `cloud-auditor.exe` from the `dist/` folder after building
locally (see **Building** below), or from a release if published. No
Python installation required to run it.

## AWS Credentials Setup

This tool reads credentials the same way the AWS CLI does:

```bash
aws configure --profile your-profile-name
```

Or set environment variables: `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`.

The IAM user/role used should have at minimum:
- `ReadOnlyAccess` (for scanning)
- `ec2:DeleteVolume`, `ec2:ReleaseAddress` (only if using cleanup)

## Usage

```bash
# Show version
cloud-auditor version

# Scan for unattached EBS volumes
cloud-auditor scan ebs --profile your-profile --region us-east-1

# Scan for unassociated Elastic IPs
cloud-auditor scan eip --profile your-profile --region us-east-1

# Scan for underutilized EC2 instances (custom lookback window)
cloud-auditor scan ec2 --profile your-profile --region us-east-1 --days 30

# Run all scanners at once
cloud-auditor scan all --profile your-profile --region us-east-1

# Export a full audit to CSV and JSON
cloud-auditor report export --profile your-profile --region us-east-1 --format both

# Preview cleanup (dry-run, default — nothing is deleted)
cloud-auditor cleanup run --profile your-profile --region us-east-1

# Actually delete flagged resources (requires typed confirmation)
cloud-auditor cleanup run --profile your-profile --region us-east-1 --execute
```

## Running Tests

```bash
python -m pytest tests/ -v
python -m pytest tests/ --cov=auditor --cov-report=term-missing
```

All tests run against `moto`-mocked AWS services — no real account or
cost required.

## Building the Standalone Executable

```bash
pip install pyinstaller
pyinstaller --onefile --name cloud-auditor --collect-all typer --collect-all rich auditor/cli.py
```

Output: `dist/cloud-auditor.exe`

## Project Structure
cloud-infra-auditor-cli/
├── auditor/
│ ├── cli.py # CLI entry point & command routing
│ ├── config.py # App-wide constants
│ ├── providers/aws/
│ │ ├── auth.py # Credential handling, role assumption
│ │ └── scanners/
│ │ ├── ebs.py # EBS volume scanner
│ │ ├── eip.py # Elastic IP scanner
│ │ ├── ec2.py # EC2 CloudWatch scanner
│ │ └── cleanup.py # Dry-run/execute cleanup logic
│ ├── reports/
│ │ ├── aggregator.py # Combines all scan results
│ │ ├── formatter.py # Rich table/panel rendering
│ │ └── exporter.py # CSV/JSON export
│ └── utils/
│ ├── regions.py # Region validation
│ ├── rate_limiter.py # Retry with exponential backoff
│ └── logger.py # App logging
├── tests/ # Full test suite (moto-based)
├── requirements.txt
├── setup.py
└── README.md
## Safety Notes

- `cleanup run` defaults to **dry-run** — no resources are ever deleted
  without the explicit `--execute` flag
- Executing cleanup requires typing an exact confirmation phrase
  matching the number of resources about to be deleted
- All cleanup actions are logged to `reports_output/cleanup_log.jsonl`
- EC2 instances are never auto-terminated by this tool — only flagged
  for human review

## License

Internal project — not currently licensed for public distribution.

# 1. Version command
python -m auditor.cli version

# 2. Top-level help shows all command groups
python -m auditor.cli --help

# 3. Each scan command's help text
python -m auditor.cli scan ebs --help
python -m auditor.cli scan eip --help
python -m auditor.cli scan ec2 --help
python -m auditor.cli scan all --help

# 4. Report export help
python -m auditor.cli report export --help

# 5. Cleanup help (dry-run default, --execute flag documented)
python -m auditor.cli cleanup run --help

# 6. Auth failure produces a clean message, not a traceback
python -m auditor.cli scan ebs --profile does-not-exist

# 7. Full test suite passes
python -m pytest tests/ -v

# 8. Coverage report generates without errors
python -m pytest tests/ --cov=auditor --cov-report=term-missing

# 9. Standalone .exe works independently
.\dist\cloud-auditor.exe version
.\dist\cloud-auditor.exe --help

# 10. Package installs in editable mode with entry point working
cloud-auditor version
