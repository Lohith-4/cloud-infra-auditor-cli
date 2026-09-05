"""
Setuptools configuration for Cloud Infrastructure Auditor & Cost Optimizer.
"""

from setuptools import setup, find_packages

setup(
    name="cloud-infra-auditor",
    version="1.0.0",
    description="CLI tool to audit cloud infrastructure for cost-saving opportunities",
    author="Lohith",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "typer[all]==0.12.3",
        "click==8.1.7",
        "rich==13.7.1",
        "boto3==1.34.144",
        "botocore==1.34.144",
        "pyyaml==6.0.1",
        "python-dateutil==2.9.0",
    ],
    entry_points={
        "console_scripts": [
            "cloud-auditor=auditor.cli:app",
        ],
    },
    python_requires=">=3.10",
)