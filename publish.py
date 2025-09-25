#!/usr/bin/env python
"""
Publishing script for vapi-manager package to PyPI.

Usage:
    python publish.py --test    # Publish to TestPyPI
    python publish.py           # Publish to PyPI
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(command, check=True):
    """Run a shell command and return the output."""
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True, check=check)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def clean_build():
    """Clean previous build artifacts."""
    print("Cleaning previous build artifacts...")
    dirs_to_clean = ["dist", "build", "*.egg-info", "vapi_manager.egg-info"]
    for dir_pattern in dirs_to_clean:
        run_command(["rm", "-rf", dir_pattern], check=False)


def build_package():
    """Build the package using poetry."""
    print("\nBuilding package...")
    result = run_command(["poetry", "build"])
    if result.returncode != 0:
        print("Build failed!")
        sys.exit(1)
    print("Build successful!")


def check_package():
    """Check package with twine."""
    print("\nChecking package with twine...")
    result = run_command(["twine", "check", "dist/*"], check=False)
    if result.returncode != 0:
        print("Package check failed! Please fix the issues before publishing.")
        sys.exit(1)
    print("Package check passed!")


def publish_to_testpypi():
    """Publish to TestPyPI."""
    print("\nPublishing to TestPyPI...")
    result = run_command([
        "poetry", "config", "repositories.testpypi",
        "https://test.pypi.org/legacy/"
    ], check=False)

    result = run_command([
        "poetry", "publish", "-r", "testpypi"
    ], check=False)

    if result.returncode != 0:
        print("\nFailed to publish to TestPyPI!")
        print("Make sure you have configured your TestPyPI credentials:")
        print("  poetry config pypi-token.testpypi YOUR_TEST_PYPI_TOKEN")
        sys.exit(1)

    print("\n✅ Successfully published to TestPyPI!")
    print("Install and test with:")
    print("  pip install -i https://test.pypi.org/simple/ vapi-manager")


def publish_to_pypi():
    """Publish to PyPI."""
    print("\nPublishing to PyPI...")

    # Confirm with user
    response = input("Are you sure you want to publish to PyPI? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled.")
        sys.exit(0)

    result = run_command(["poetry", "publish"], check=False)

    if result.returncode != 0:
        print("\nFailed to publish to PyPI!")
        print("Make sure you have configured your PyPI credentials:")
        print("  poetry config pypi-token.pypi YOUR_PYPI_TOKEN")
        sys.exit(1)

    print("\n✅ Successfully published to PyPI!")
    print("Install with:")
    print("  pip install vapi-manager")


def main():
    parser = argparse.ArgumentParser(description="Publish vapi-manager to PyPI")
    parser.add_argument("--test", action="store_true",
                      help="Publish to TestPyPI instead of PyPI")
    parser.add_argument("--no-build", action="store_true",
                      help="Skip building (use existing dist)")
    parser.add_argument("--no-check", action="store_true",
                      help="Skip package checks")
    parser.add_argument("--clean", action="store_true",
                      help="Clean build artifacts and exit")

    args = parser.parse_args()

    if args.clean:
        clean_build()
        print("Clean complete.")
        sys.exit(0)

    if not args.no_build:
        clean_build()
        build_package()

    if not args.no_check:
        # Install twine if not available
        run_command(["pip", "install", "--quiet", "twine"], check=False)
        check_package()

    if args.test:
        publish_to_testpypi()
    else:
        publish_to_pypi()


if __name__ == "__main__":
    main()