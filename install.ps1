# News CLI Installer for Windows
# Run in PowerShell as Administrator
# Usage: irm https://raw.githubusercontent.com/ikenai-lab/news-cli/main/install.ps1 | iex

Write-Host "🚀 News CLI Installer for Windows" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

function Test-Command {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Install-Uv {
    Write-Host "`n📦 Installing uv (Python package manager)..." -ForegroundColor Yellow
    
    # Check if winget is available
    if (Test-Command "winget") {
        winget install --id=astral-sh.uv -e --accept-package-agreements --accept-source-agreements
    } else {
        # Fallback to PowerShell installer
        irm https://astral.sh/uv/install.ps1 | iex
    }
    
    Write-Host "✓ uv installed successfully" -ForegroundColor Green
}

function Install-Ollama {
    Write-Host "`n🤖 Installing Ollama (Local LLM runtime)..." -ForegroundColor Yellow
    
    if (Test-Command "winget") {
        winget install --id=Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host "Please install Ollama manually from: https://ollama.com/download" -ForegroundColor Red
        Write-Host "Press any key to continue after installation..." -ForegroundColor Yellow
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
    
    Write-Host "✓ Ollama installed successfully" -ForegroundColor Green
}

function Install-Git {
    Write-Host "`n📂 Installing Git..." -ForegroundColor Yellow
    
    if (Test-Command "winget") {
        winget install --id=Git.Git -e --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host "Please install Git manually from: https://git-scm.com/download/win" -ForegroundColor Red
        exit 1
    }
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    Write-Host "✓ Git installed successfully" -ForegroundColor Green
}

# Main installation
Write-Host "Checking dependencies..." -ForegroundColor Cyan
Write-Host ""

# Check Git
if (Test-Command "git") {
    Write-Host "✓ git is installed" -ForegroundColor Green
} else {
    Write-Host "✗ git is not installed" -ForegroundColor Yellow
    $response = Read-Host "Install Git? (y/n)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Install-Git
    } else {
        Write-Host "Error: Git is required. Exiting." -ForegroundColor Red
        exit 1
    }
}

# Check uv
if (Test-Command "uv") {
    Write-Host "✓ uv is installed" -ForegroundColor Green
} else {
    Write-Host "✗ uv is not installed" -ForegroundColor Yellow
    $response = Read-Host "Install uv? (y/n)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Install-Uv
    } else {
        Write-Host "Error: uv is required. Exiting." -ForegroundColor Red
        exit 1
    }
}

# Check Ollama
if (Test-Command "ollama") {
    Write-Host "✓ ollama is installed" -ForegroundColor Green
} else {
    Write-Host "✗ ollama is not installed" -ForegroundColor Yellow
    $response = Read-Host "Install Ollama? (y/n)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Install-Ollama
    } else {
        Write-Host "Error: Ollama is required. Exiting." -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n📂 Cloning repository..." -ForegroundColor Cyan

# Clone the repository
if (Test-Path "news-cli") {
    Write-Host "Directory 'news-cli' already exists. Updating..."
    Set-Location news-cli
    git pull
} else {
    git clone https://github.com/ikenai-lab/news-cli.git
    Set-Location news-cli
}

Write-Host "`n📦 Installing Python dependencies..." -ForegroundColor Cyan
uv sync

Write-Host "`n🌐 Installing browser for JavaScript sites (optional)..." -ForegroundColor Cyan
try {
    uv run playwright install chromium
} catch {
    Write-Host "Playwright install skipped" -ForegroundColor Yellow
}

Write-Host "`n🤖 Pulling LLM model (llama3.2:3b)..." -ForegroundColor Cyan
ollama pull llama3.2:3b

Write-Host ""
Write-Host "✅ Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To run News CLI:" -ForegroundColor Cyan
Write-Host "  cd news-cli"
Write-Host "  uv run news-cli"
Write-Host ""
