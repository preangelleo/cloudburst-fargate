#!/usr/bin/env python3
"""
Setup script for cloudburst-fargate package
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# Get version from version.py
exec(open('cloudburst_fargate/version.py').read())

setup(
    name="cloudburst-fargate",
    version=__version__,
    author="Leo Wang",
    author_email="me@leowang.net",
    description="Serverless video processing using AWS ECS Fargate",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/preangelleo/cloudburst-fargate",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=22.0",
            "flake8>=4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cloudburst-fargate=cloudburst_fargate.cli:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/preangelleo/cloudburst-fargate/issues",
        "Source": "https://github.com/preangelleo/cloudburst-fargate",
        "Documentation": "https://github.com/preangelleo/cloudburst-fargate/blob/main/README.md",
    },
)