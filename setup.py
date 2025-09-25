#!/usr/bin/env python
"""
Setup script for vapi-manager package.
This file is maintained for backward compatibility with older pip versions.
The main configuration is in pyproject.toml.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read version from package
version_file = this_directory / "vapi_manager" / "__version__.py"
version = {}
if version_file.exists():
    exec(version_file.read_text(), version)
    VERSION = version.get("__version__", "1.0.0")
else:
    VERSION = "1.0.0"

setup(
    name="vapi-manager",
    version=VERSION,
    description="A comprehensive CLI tool for managing VAPI assistants and squads",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="VAPI Manager Team",
    author_email="support@vapi-manager.io",
    url="https://github.com/vapi-ai/vapi-manager",
    project_urls={
        "Bug Tracker": "https://github.com/vapi-ai/vapi-manager/issues",
        "Documentation": "https://docs.vapi-manager.io",
        "Source Code": "https://github.com/vapi-ai/vapi-manager",
        "Changelog": "https://github.com/vapi-ai/vapi-manager/blob/main/CHANGELOG.md",
    },
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Communications :: Telephony",
        "Topic :: System :: Systems Administration",
        "Typing :: Typed",
    ],
    keywords=[
        "vapi",
        "assistant",
        "squad",
        "cli",
        "management",
        "ai",
        "automation",
        "deployment",
        "voice",
        "telephony"
    ],
    packages=find_packages(exclude=["tests*", "docs*"]),
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.8.0",
        "httpx>=0.27.0",
        "python-dotenv>=1.0.0",
        "typer>=0.9.0",
        "rich>=13.7.0",
        "pydantic-settings>=2.4.0",
        "pyyaml>=6.0",
        "jinja2>=3.1.6",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.24.0",
            "pytest-cov>=5.0.0",
            "black>=24.0.0",
            "ruff>=0.6.0",
            "mypy>=1.11.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=2.0.0",
            "sphinx-autodoc-typehints>=1.25.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vapi-manager=vapi_manager.cli.simple_cli:main",
            "vapi=vapi_manager.cli.simple_cli:main",
            "vapictl=vapi_manager.cli.simple_cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "vapi_manager": [
            "templates/**/*",
            "shared/**/*",
        ],
    },
    zip_safe=False,
)