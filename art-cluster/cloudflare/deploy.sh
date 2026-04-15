#!/bin/bash
# Deployment script for mirror3.openshift.com Cloudflare Worker

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v wrangler &> /dev/null; then
        log_error "wrangler CLI not found. Install with: npm install -g wrangler"
        exit 1
    fi

    if ! command -v npm &> /dev/null; then
        log_error "npm not found. Please install Node.js and npm"
        exit 1
    fi

    log_info "Prerequisites check passed"
}

# Verify wrangler authentication
check_auth() {
    log_info "Checking Cloudflare authentication..."

    if ! wrangler whoami &> /dev/null; then
        log_error "Not authenticated with Cloudflare. Run: wrangler login"
        exit 1
    fi

    log_info "Authenticated with Cloudflare"
}

# Verify R2 bucket exists
check_r2_bucket() {
    log_info "Checking R2 bucket 'art-srv-enterprise'..."

    if wrangler r2 bucket list | grep -q "art-srv-enterprise"; then
        log_info "R2 bucket 'art-srv-enterprise' found"
    else
        log_warn "R2 bucket 'art-srv-enterprise' not found"
        read -p "Create bucket? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            wrangler r2 bucket create art-srv-enterprise
            log_info "Created R2 bucket 'art-srv-enterprise'"
        else
            log_error "Cannot proceed without R2 bucket"
            exit 1
        fi
    fi
}

# Check if secrets are configured
check_secrets() {
    log_info "Checking secrets configuration..."

    if ! wrangler secret list | grep -q "ENTERPRISE_SERVICE_ACCOUNTS"; then
        log_warn "ENTERPRISE_SERVICE_ACCOUNTS secret not set"
        echo "You'll need to set this secret with: wrangler secret put ENTERPRISE_SERVICE_ACCOUNTS"
    fi

    if ! wrangler secret list | grep -q "POCKETS_SERVICE_ACCOUNTS"; then
        log_warn "POCKETS_SERVICE_ACCOUNTS secret not set"
        echo "You'll need to set this secret with: wrangler secret put POCKETS_SERVICE_ACCOUNTS"
    fi
}

# Install dependencies
install_deps() {
    log_info "Installing dependencies..."
    npm install
    log_info "Dependencies installed"
}

# Build and deploy
deploy() {
    log_info "Building and deploying worker..."

    wrangler deploy

    log_info "Deployment complete!"
    echo ""
    echo "Next steps:"
    echo "1. Configure custom domain for mirror3.openshift.com"
    echo "   - Via CLI: wrangler deploy --routes 'mirror3.openshift.com/*'"
    echo "   - Via Dashboard: Workers → openshift-mirror-list → Settings → Triggers → Add Custom Domain"
    echo ""
    echo "2. Verify DNS is configured for mirror3.openshift.com"
    echo ""
    echo "3. Test deployment:"
    echo "   - Public: curl https://mirror3.openshift.com/pub/"
    echo "   - Private: curl -u user:pass https://mirror3.openshift.com/enterprise/"
    echo ""
    echo "4. Monitor logs: wrangler tail"
}

# Main deployment flow
main() {
    echo "========================================="
    echo "  mirror3.openshift.com Deployment"
    echo "========================================="
    echo ""

    check_prerequisites
    check_auth
    check_r2_bucket
    install_deps
    check_secrets

    echo ""
    read -p "Proceed with deployment? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        deploy
    else
        log_warn "Deployment cancelled"
        exit 0
    fi
}

# Handle script arguments
case "${1:-deploy}" in
    check)
        check_prerequisites
        check_auth
        check_r2_bucket
        check_secrets
        ;;
    install)
        install_deps
        ;;
    deploy)
        main
        ;;
    secrets)
        log_info "Setting up secrets..."
        echo "Setting ENTERPRISE_SERVICE_ACCOUNTS..."
        wrangler secret put ENTERPRISE_SERVICE_ACCOUNTS
        echo "Setting POCKETS_SERVICE_ACCOUNTS..."
        wrangler secret put POCKETS_SERVICE_ACCOUNTS
        log_info "Secrets configured"
        ;;
    *)
        echo "Usage: $0 {check|install|deploy|secrets}"
        echo ""
        echo "Commands:"
        echo "  check   - Check prerequisites and configuration"
        echo "  install - Install npm dependencies"
        echo "  deploy  - Full deployment (default)"
        echo "  secrets - Configure secrets interactively"
        exit 1
        ;;
esac
