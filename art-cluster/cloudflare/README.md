# Cloudflare Worker for mirror3.openshift.com

## Overview

This Cloudflare Worker serves as the backend for **mirror3.openshift.com**, migrating from AWS CloudFront to Cloudflare. It provides access to OpenShift artifacts stored in the Cloudflare R2 bucket `art-srv-enterprise`.

This is part of the migration from CloudFront to Cloudflare infrastructure for serving OpenShift release artifacts.

## Key Features

- **Access Control**: Implements secure Basic Authentication to protect private paths, ensuring only authorized users can access resources under `/enterprise`, `/libra`, and `/pockets` directories.
- **Public Access**: Provides unauthenticated access to `/pub` paths for public OpenShift artifacts.
- **Secrets Management**: Manages sensitive credentials for service accounts using Cloudflare secrets (environment variables).
- **File Management**: Handles file listing, downloading, and object storage within R2 buckets, including support for dynamic path management and rendering of directory listings.
- **Path Replacements**: Handles legacy single-arch redirects (e.g., `/pub/openshift-v4/clients` → `/pub/openshift-v4/x86_64/clients`)
- **CGW Proxy**: Proxies certain paths to Red Hat Content Gateway for teams hosting their own content.

## How It Works

The worker intercepts requests to mirror3.openshift.com and:
1. Checks if the path requires authentication (`/enterprise`, `/libra`, `/pockets`)
2. Verifies credentials using Base64-encoded Basic Auth
3. Applies path replacements for legacy arch-specific URLs
4. Proxies certain paths to Red Hat Content Gateway (CGW)
5. Serves content from the R2 bucket or generates directory listings
6. Returns appropriate responses (files, listings, or errors)

## Quick Start

### Prerequisites
- Node.js and npm installed
- Wrangler CLI: `npm install -g wrangler`
- Cloudflare account with R2 enabled
- R2 bucket `art-srv-enterprise` created and populated with content

### Deployment

**Option 1: Using the deployment script (recommended)**
```bash
# Check prerequisites and configuration
./deploy.sh check

# Configure secrets
./deploy.sh secrets

# Deploy to Cloudflare
./deploy.sh deploy
```

**Option 2: Manual deployment**
```bash
# Install dependencies
npm install

# Configure secrets
wrangler secret put ENTERPRISE_SERVICE_ACCOUNTS
wrangler secret put POCKETS_SERVICE_ACCOUNTS

# Deploy worker
wrangler deploy

# Add custom domain
wrangler deploy --routes "mirror3.openshift.com/*"
```

For detailed deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## Configuration

### R2 Bucket Binding
Configured in `wrangler.toml`:
```toml
r2_buckets = [
    { binding = "BUCKET_bucketname", bucket_name = "art-srv-enterprise" }
]
```

### Domain Configuration
Configured in `src/config.ts` with support for:
- Public paths: `/pub`
- Private paths: `/enterprise`, `/libra`, `/pockets`
- Path replacements for legacy arch URLs
- CGW proxy endpoints

### Secrets Format
Secrets should be JSON objects with username:password pairs:
```json
{
  "username1": "password1",
  "username2": "password2"
}
```

For `/pockets` paths, usernames must follow the format: `<pocket_name>+<random_id>`

## Testing

```bash
# Test public access
curl https://mirror3.openshift.com/pub/

# Test authenticated access
curl -u username:password https://mirror3.openshift.com/enterprise/

# Test path replacement
curl https://mirror3.openshift.com/pub/openshift-v4/clients/

# Monitor logs
wrangler tail
```

## Project Structure

```
cloudflare/
├── src/
│   ├── index.ts          # Main worker entry point
│   ├── config.ts         # Domain and site configuration
│   ├── types.ts          # TypeScript type definitions
│   ├── checkAccess.ts    # Authentication logic
│   └── render.ts         # Directory listing renderer
├── wrangler.toml         # Wrangler configuration
├── deploy.sh             # Deployment helper script
├── DEPLOYMENT.md         # Detailed deployment guide
└── README.md             # This file
```

## Migration from CloudFront

This worker replaces the AWS CloudFront + Lambda@Edge setup documented in `../cloudfront/mirror/README.md`.

Key differences:
- **Storage**: AWS S3 → Cloudflare R2
- **CDN**: AWS CloudFront → Cloudflare Workers
- **Functions**: Lambda@Edge → Cloudflare Workers
- **Secrets**: AWS Secrets Manager → Cloudflare Secrets

The functionality remains the same: authentication, directory listings, path replacements, and CGW proxying.

## Troubleshooting

See [DEPLOYMENT.md](./DEPLOYMENT.md) for common issues and solutions.

## Related Documentation

- [CloudFront Mirror Documentation](../cloudfront/mirror/README.md) - Legacy AWS setup
- [Cloudflare Workers Docs](https://developers.cloudflare.com/workers/)
- [Cloudflare R2 Docs](https://developers.cloudflare.com/r2/)

