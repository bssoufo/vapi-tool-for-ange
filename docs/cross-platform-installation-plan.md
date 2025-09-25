# Cross-Platform Installation Plan for VAPI Manager

## Executive Summary
A comprehensive plan to make vapi-manager installable and usable as a CLI tool across Windows, macOS, and Linux, with multiple installation methods to suit different user preferences and technical expertise levels.

## Installation Methods Overview

### 1. **PyPI Package (Primary Method)**
- Most universal and Python-native approach
- Works on all platforms with Python installed
- Simple installation via pip

### 2. **Standalone Executables**
- No Python required on target system
- Platform-specific binaries
- Ideal for non-technical users

### 3. **Package Managers**
- Homebrew (macOS/Linux)
- Chocolatey/Scoop (Windows)
- APT/YUM/DNF (Linux)

### 4. **Docker Container**
- Ultimate portability
- Consistent environment
- DevOps-friendly

### 5. **Install Script**
- One-line installation
- Handles dependencies and PATH setup
- Platform detection

## Detailed Implementation Plan

## Phase 1: PyPI Package Distribution

### 1.1 Package Configuration
```toml
# pyproject.toml updates
[tool.poetry]
name = "vapi-manager"
version = "1.0.0"
description = "VAPI Assistant and Squad Management Tool"
license = "MIT"
authors = ["Your Team <team@example.com>"]
readme = "README.md"
homepage = "https://github.com/yourorg/vapi-manager"
repository = "https://github.com/yourorg/vapi-manager"
documentation = "https://vapi-manager.readthedocs.io"
keywords = ["vapi", "assistant", "squad", "cli", "management"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Operating System :: OS Independent",
    "Environment :: Console",
]
packages = [{include = "vapi_manager"}]

[tool.poetry.dependencies]
python = "^3.8"  # Lower minimum version for wider compatibility

[tool.poetry.scripts]
vapi-manager = "vapi_manager.cli.simple_cli:main"
vapi = "vapi_manager.cli.simple_cli:main"  # Short alias

[tool.poetry.urls]
"Bug Tracker" = "https://github.com/yourorg/vapi-manager/issues"
```

### 1.2 Publishing Process
```bash
# Build package
poetry build

# Publish to TestPyPI first
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry publish -r testpypi

# Publish to PyPI
poetry publish
```

### 1.3 Installation Instructions
```bash
# Standard installation
pip install vapi-manager

# With specific Python version
python3 -m pip install vapi-manager

# Development installation
pip install vapi-manager[dev]
```

## Phase 2: Standalone Executables

### 2.1 PyInstaller Configuration
```python
# build_standalone.py
import PyInstaller.__main__
import platform
import sys

def build_executable():
    system = platform.system().lower()

    args = [
        'vapi_manager/cli/simple_cli.py',
        '--name=vapi-manager',
        '--onefile',
        '--console',
        '--add-data=vapi_manager/templates:templates',
        '--add-data=shared:shared',
        '--hidden-import=yaml',
        '--hidden-import=httpx',
        '--hidden-import=pydantic',
    ]

    if system == 'windows':
        args.extend([
            '--icon=assets/icon.ico',
            '--version-file=version_info.txt'
        ])
    elif system == 'darwin':
        args.extend([
            '--icon=assets/icon.icns',
            '--osx-bundle-identifier=com.yourorg.vapi-manager'
        ])

    PyInstaller.__main__.run(args)

if __name__ == '__main__':
    build_executable()
```

### 2.2 GitHub Actions Build Pipeline
```yaml
# .github/workflows/build-standalone.yml
name: Build Standalone Executables

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.11']

    runs-on: ${{ matrix.os }}

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install poetry pyinstaller
        poetry install

    - name: Build executable
      run: python build_standalone.py

    - name: Upload artifact
      uses: actions/upload-artifact@v3
      with:
        name: vapi-manager-${{ matrix.os }}
        path: dist/vapi-manager*
```

## Phase 3: Package Manager Integration

### 3.1 Homebrew Formula (macOS/Linux)
```ruby
# homebrew-vapi-manager/Formula/vapi-manager.rb
class VapiManager < Formula
  include Language::Python::Virtualenv

  desc "VAPI Assistant and Squad Management Tool"
  homepage "https://github.com/yourorg/vapi-manager"
  url "https://pypi.io/packages/source/v/vapi-manager/vapi-manager-1.0.0.tar.gz"
  sha256 "YOUR_SHA256_HERE"
  license "MIT"

  depends_on "python@3.11"

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/..."
    sha256 "..."
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/vapi-manager", "--version"
  end
end
```

### 3.2 Chocolatey Package (Windows)
```xml
<!-- chocolatey/vapi-manager.nuspec -->
<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd">
  <metadata>
    <id>vapi-manager</id>
    <version>1.0.0</version>
    <title>VAPI Manager</title>
    <authors>Your Team</authors>
    <projectUrl>https://github.com/yourorg/vapi-manager</projectUrl>
    <description>VAPI Assistant and Squad Management Tool</description>
    <tags>vapi cli assistant squad management</tags>
  </metadata>
  <files>
    <file src="tools\**" target="tools" />
  </files>
</package>
```

### 3.3 Scoop Manifest (Windows)
```json
{
    "version": "1.0.0",
    "description": "VAPI Assistant and Squad Management Tool",
    "homepage": "https://github.com/yourorg/vapi-manager",
    "license": "MIT",
    "architecture": {
        "64bit": {
            "url": "https://github.com/yourorg/vapi-manager/releases/download/v1.0.0/vapi-manager-win64.exe",
            "hash": "sha256:YOUR_HASH_HERE"
        }
    },
    "bin": "vapi-manager.exe",
    "checkver": "github",
    "autoupdate": {
        "architecture": {
            "64bit": {
                "url": "https://github.com/yourorg/vapi-manager/releases/download/v$version/vapi-manager-win64.exe"
            }
        }
    }
}
```

## Phase 4: Docker Container

### 4.1 Dockerfile
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY vapi_manager ./vapi_manager
COPY shared ./shared
COPY templates ./templates

# Install poetry and dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Create volume mount points
VOLUME ["/workspace/assistants", "/workspace/squads"]

# Set environment variables
ENV VAPI_API_KEY=""
ENV PYTHONUNBUFFERED=1

# Create entrypoint script
RUN echo '#!/bin/bash\nvapi-manager "$@"' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["--help"]
```

### 4.2 Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  vapi-manager:
    image: vapi-manager:latest
    environment:
      - VAPI_API_KEY=${VAPI_API_KEY}
    volumes:
      - ./assistants:/workspace/assistants
      - ./squads:/workspace/squads
      - ./shared:/workspace/shared
    working_dir: /workspace
```

## Phase 5: Universal Install Script

### 5.1 Cross-Platform Install Script
```bash
#!/usr/bin/env bash
# install.sh - Universal installer for vapi-manager

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Check Python installation
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}Python is not installed. Please install Python 3.8 or later.${NC}"
        exit 1
    fi

    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    REQUIRED_VERSION="3.8"

    if [[ $(echo "$PYTHON_VERSION < $REQUIRED_VERSION" | bc) -eq 1 ]]; then
        echo -e "${RED}Python $REQUIRED_VERSION or later is required. Found: $PYTHON_VERSION${NC}"
        exit 1
    fi
}

# Install via pip
install_pip() {
    echo -e "${GREEN}Installing vapi-manager via pip...${NC}"
    $PYTHON_CMD -m pip install --upgrade pip
    $PYTHON_CMD -m pip install vapi-manager
}

# Install via homebrew
install_homebrew() {
    echo -e "${GREEN}Installing vapi-manager via Homebrew...${NC}"
    brew tap yourorg/vapi-manager
    brew install vapi-manager
}

# Install via chocolatey
install_chocolatey() {
    echo -e "${GREEN}Installing vapi-manager via Chocolatey...${NC}"
    choco install vapi-manager -y
}

# Download standalone executable
install_standalone() {
    OS=$1
    ARCH=$(uname -m)

    echo -e "${GREEN}Downloading standalone executable...${NC}"

    case $OS in
        linux)
            URL="https://github.com/yourorg/vapi-manager/releases/latest/download/vapi-manager-linux-$ARCH"
            DEST="/usr/local/bin/vapi-manager"
            ;;
        macos)
            URL="https://github.com/yourorg/vapi-manager/releases/latest/download/vapi-manager-macos-$ARCH"
            DEST="/usr/local/bin/vapi-manager"
            ;;
        windows)
            URL="https://github.com/yourorg/vapi-manager/releases/latest/download/vapi-manager-windows.exe"
            DEST="$HOME/AppData/Local/Programs/vapi-manager/vapi-manager.exe"
            mkdir -p "$HOME/AppData/Local/Programs/vapi-manager"
            ;;
    esac

    curl -L -o "$DEST" "$URL"
    chmod +x "$DEST"

    # Add to PATH for Windows
    if [[ $OS == "windows" ]]; then
        setx PATH "%PATH%;$HOME\AppData\Local\Programs\vapi-manager"
    fi
}

# Configure shell completion
setup_completion() {
    SHELL_TYPE=$(basename "$SHELL")

    case $SHELL_TYPE in
        bash)
            echo 'eval "$(_VAPI_MANAGER_COMPLETE=bash_source vapi-manager)"' >> ~/.bashrc
            ;;
        zsh)
            echo 'eval "$(_VAPI_MANAGER_COMPLETE=zsh_source vapi-manager)"' >> ~/.zshrc
            ;;
        fish)
            vapi-manager --install-completion fish
            ;;
    esac
}

# Main installation flow
main() {
    echo -e "${YELLOW}VAPI Manager Installer${NC}"
    echo "========================"

    OS=$(detect_os)
    echo "Detected OS: $OS"

    # Offer installation methods
    echo ""
    echo "Choose installation method:"
    echo "1) pip (recommended)"
    echo "2) Standalone executable"

    if [[ $OS == "macos" ]] && command -v brew &> /dev/null; then
        echo "3) Homebrew"
    fi

    if [[ $OS == "windows" ]] && command -v choco &> /dev/null; then
        echo "3) Chocolatey"
    fi

    read -p "Enter choice [1]: " choice
    choice=${choice:-1}

    case $choice in
        1)
            check_python
            install_pip
            ;;
        2)
            install_standalone $OS
            ;;
        3)
            if [[ $OS == "macos" ]]; then
                install_homebrew
            elif [[ $OS == "windows" ]]; then
                install_chocolatey
            fi
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            exit 1
            ;;
    esac

    # Setup shell completion
    read -p "Setup shell completion? [Y/n]: " setup_comp
    if [[ $setup_comp != "n" ]]; then
        setup_completion
    fi

    # Verify installation
    if command -v vapi-manager &> /dev/null; then
        echo -e "${GREEN}✓ Installation successful!${NC}"
        echo "Run 'vapi-manager --help' to get started"
    else
        echo -e "${RED}✗ Installation may have failed. Please check the output above.${NC}"
    fi
}

# Run main function
main
```

### 5.2 PowerShell Install Script (Windows)
```powershell
# install.ps1 - Windows PowerShell installer

$ErrorActionPreference = "Stop"

function Write-Color($Text, $Color = "White") {
    Write-Host $Text -ForegroundColor $Color
}

function Test-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-VapiManager {
    Write-Color "VAPI Manager Installer for Windows" "Yellow"
    Write-Color "===================================" "Yellow"

    # Check for package managers
    $hasChoco = Get-Command choco -ErrorAction SilentlyContinue
    $hasScoop = Get-Command scoop -ErrorAction SilentlyContinue
    $hasPython = Get-Command python -ErrorAction SilentlyContinue

    $methods = @()
    if ($hasPython) { $methods += "pip" }
    if ($hasChoco) { $methods += "chocolatey" }
    if ($hasScoop) { $methods += "scoop" }
    $methods += "standalone"

    Write-Host ""
    Write-Host "Available installation methods:"
    for ($i = 0; $i -lt $methods.Length; $i++) {
        Write-Host "$($i+1)) $($methods[$i])"
    }

    $choice = Read-Host "Choose installation method [1]"
    if ([string]::IsNullOrWhiteSpace($choice)) { $choice = "1" }

    $method = $methods[[int]$choice - 1]

    switch ($method) {
        "pip" {
            Write-Color "Installing via pip..." "Green"
            python -m pip install --upgrade pip
            python -m pip install vapi-manager
        }
        "chocolatey" {
            if (-not (Test-Admin)) {
                Write-Color "Administrator privileges required for Chocolatey" "Red"
                exit 1
            }
            Write-Color "Installing via Chocolatey..." "Green"
            choco install vapi-manager -y
        }
        "scoop" {
            Write-Color "Installing via Scoop..." "Green"
            scoop bucket add vapi-manager https://github.com/yourorg/scoop-vapi-manager
            scoop install vapi-manager
        }
        "standalone" {
            Write-Color "Downloading standalone executable..." "Green"
            $url = "https://github.com/yourorg/vapi-manager/releases/latest/download/vapi-manager-windows.exe"
            $dest = "$env:LOCALAPPDATA\Programs\vapi-manager"

            New-Item -ItemType Directory -Force -Path $dest | Out-Null
            Invoke-WebRequest -Uri $url -OutFile "$dest\vapi-manager.exe"

            # Add to PATH
            $path = [Environment]::GetEnvironmentVariable("PATH", "User")
            if ($path -notlike "*$dest*") {
                [Environment]::SetEnvironmentVariable("PATH", "$path;$dest", "User")
                Write-Color "Added to PATH. Please restart your terminal." "Yellow"
            }
        }
    }

    # Verify installation
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    if (Get-Command vapi-manager -ErrorAction SilentlyContinue) {
        Write-Color "✓ Installation successful!" "Green"
        Write-Color "Run 'vapi-manager --help' to get started" "Cyan"
    } else {
        Write-Color "✗ Installation may have failed. Please check the output above." "Red"
    }
}

# Run installer
Install-VapiManager
```

## Phase 6: PATH Configuration

### 6.1 Automatic PATH Setup
```python
# vapi_manager/utils/path_setup.py
import os
import platform
import subprocess
from pathlib import Path

def setup_path():
    """Add vapi-manager to system PATH"""
    system = platform.system()

    if system == "Windows":
        setup_windows_path()
    elif system == "Darwin":
        setup_macos_path()
    elif system == "Linux":
        setup_linux_path()

def setup_windows_path():
    """Add to Windows PATH via registry"""
    import winreg

    vapi_path = Path(__file__).parent.parent

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                       r"Environment",
                       0,
                       winreg.KEY_ALL_ACCESS) as key:
        try:
            path, _ = winreg.QueryValueEx(key, "PATH")
            if str(vapi_path) not in path:
                new_path = f"{path};{vapi_path}"
                winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
        except FileNotFoundError:
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, str(vapi_path))

def setup_macos_path():
    """Add to macOS PATH via shell profile"""
    shell_profile = Path.home() / ".zshrc"  # Default for macOS Catalina+
    if not shell_profile.exists():
        shell_profile = Path.home() / ".bash_profile"

    vapi_path = Path(__file__).parent.parent
    export_line = f'\nexport PATH="$PATH:{vapi_path}"\n'

    with open(shell_profile, 'a') as f:
        f.write(export_line)

def setup_linux_path():
    """Add to Linux PATH via shell profile"""
    shell = os.environ.get('SHELL', '/bin/bash')

    if 'zsh' in shell:
        profile = Path.home() / ".zshrc"
    elif 'bash' in shell:
        profile = Path.home() / ".bashrc"
    else:
        profile = Path.home() / ".profile"

    vapi_path = Path(__file__).parent.parent
    export_line = f'\nexport PATH="$PATH:{vapi_path}"\n'

    with open(profile, 'a') as f:
        f.write(export_line)
```

## Phase 7: Testing Strategy

### 7.1 Cross-Platform Test Matrix
```yaml
# .github/workflows/test-installation.yml
name: Test Installation Methods

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test-pip:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python: ['3.8', '3.9', '3.10', '3.11', '3.12']

    runs-on: ${{ matrix.os }}

    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python }}

    - name: Test pip installation
      run: |
        pip install .
        vapi-manager --version
        vapi-manager --help

  test-standalone:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]

    runs-on: ${{ matrix.os }}

    steps:
    - uses: actions/checkout@v3

    - name: Build and test standalone
      run: |
        python build_standalone.py
        ./dist/vapi-manager --version

  test-docker:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Build and test Docker image
      run: |
        docker build -t vapi-manager .
        docker run vapi-manager --version
```

## Phase 8: Documentation

### 8.1 Installation Guide
```markdown
# Installation Guide

## Quick Install

### Universal (All Platforms)
```bash
curl -sSL https://install.vapi-manager.io | bash
```

### Windows PowerShell
```powershell
iwr -useb https://install.vapi-manager.io/windows | iex
```

## Package Managers

### pip (Python)
```bash
pip install vapi-manager
```

### Homebrew (macOS/Linux)
```bash
brew install vapi-manager
```

### Chocolatey (Windows)
```powershell
choco install vapi-manager
```

### Scoop (Windows)
```powershell
scoop install vapi-manager
```

## Docker
```bash
docker pull vapi-manager:latest
docker run -v $(pwd):/workspace vapi-manager --help
```

## Verify Installation
```bash
vapi-manager --version
```
```

## Implementation Timeline

### Week 1-2: PyPI Package
- Configure package metadata
- Test on TestPyPI
- Publish to PyPI
- Create installation documentation

### Week 3-4: Standalone Executables
- Setup PyInstaller builds
- Configure GitHub Actions
- Test on all platforms
- Create release pipeline

### Week 5-6: Package Managers
- Create Homebrew formula
- Create Chocolatey package
- Create Scoop manifest
- Submit to repositories

### Week 7: Docker & Scripts
- Build Docker image
- Create install scripts
- Test all installation methods
- Update documentation

### Week 8: Polish & Launch
- Complete testing matrix
- Update all documentation
- Create landing page
- Official release

## Success Metrics

1. **Installation Success Rate**: >95% across all platforms
2. **Time to Install**: <2 minutes for any method
3. **Platform Coverage**: Windows, macOS, Linux fully supported
4. **User Satisfaction**: Easy installation reported by >90% of users

## Maintenance Plan

1. **Automated Releases**: GitHub Actions for all platforms
2. **Version Management**: Semantic versioning with changelog
3. **Update Notifications**: Built-in update checker
4. **Backward Compatibility**: Support last 3 major versions

This comprehensive plan ensures vapi-manager will be easily installable and usable across all major operating systems with multiple installation options to suit different user preferences and technical levels.