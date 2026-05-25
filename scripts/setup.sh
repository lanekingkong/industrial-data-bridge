#!/usr/bin/env bash
# Industrial Data Bridge - Setup Script
# This script sets up the development environment

set -e

echo "=========================================="
echo "Industrial Data Bridge - Setup Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python version
print_info "Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
python_major=$(echo $python_version | cut -d. -f1)
python_minor=$(echo $python_version | cut -d. -f2)

if [[ $python_major -lt 3 ]] || [[ $python_minor -lt 9 ]]; then
    print_error "Python 3.9 or higher is required. Found Python $python_version"
    exit 1
fi
print_success "Python $python_version detected"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    print_error "Could not find virtual environment activation script"
    exit 1
fi
print_success "Virtual environment activated"

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip
print_success "pip upgraded"

# Install dependencies
print_info "Installing core dependencies..."
pip install -r requirements.txt
print_success "Core dependencies installed"

# Install development dependencies (optional)
if [ "$1" = "--dev" ] || [ "$1" = "-d" ]; then
    print_info "Installing development dependencies..."
    pip install -r requirements-dev.txt
    print_success "Development dependencies installed"
fi

# Install edge dependencies (optional)
if [ "$1" = "--edge" ] || [ "$1" = "-e" ]; then
    print_info "Installing edge computing dependencies..."
    pip install -r requirements-edge.txt
    print_success "Edge dependencies installed"
fi

# Create .env file from example
if [ ! -f ".env" ]; then
    print_info "Creating .env file from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_warning "Please update the .env file with your configuration"
    else
        print_error ".env.example not found"
    fi
else
    print_info ".env file already exists"
fi

# Create necessary directories
print_info "Creating necessary directories..."
mkdir -p logs data models backups
print_success "Directories created"

# Initialize database (if PostgreSQL is available)
read -p "Do you want to initialize the database? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Initializing database..."
    if command -v psql &> /dev/null; then
        python scripts/init_db.py init
        print_success "Database initialized"
    else
        print_warning "PostgreSQL not found. Database initialization skipped."
        print_warning "Install PostgreSQL and run: python scripts/init_db.py init"
    fi
fi

# Run diagnostics
print_info "Running system diagnostics..."
python scripts/diagnose.py --output text
print_success "Diagnostics completed"

# Set up pre-commit hooks (if installed)
if command -v pre-commit &> /dev/null; then
    print_info "Setting up pre-commit hooks..."
    pre-commit install
    print_success "Pre-commit hooks installed"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update the .env file with your configuration"
echo "2. Start the development server: python -m src.main"
echo "3. Or use Docker: docker-compose up"
echo ""
echo "Useful commands:"
echo "  python scripts/diagnose.py    - Run system diagnostics"
echo "  python scripts/init_db.py     - Database management"
echo "  pytest                         - Run tests"
echo "  black src/                     - Format code"
echo "  mypy src/                      - Type checking"
echo ""
echo "Documentation:"
echo "  Read docs/ for detailed documentation"
echo "  Check examples/ for usage examples"
echo ""
echo "=========================================="