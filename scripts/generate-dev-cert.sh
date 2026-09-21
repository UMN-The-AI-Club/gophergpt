#!/usr/bin/env bash

set -euo pipefail

# Find the root of the GopherGPT repository.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Create the certs directory if it does not already exist.
CERT_DIR="$REPO_ROOT/certs"
mkdir -p "$CERT_DIR"

echo "Generating self-signed HTTPS certificate for localhost..."

docker run --rm \
    -v "$CERT_DIR:/certs" \
    alpine sh -c \
    "apk add --no-cache openssl && \
    openssl req \
        -x509 \
        -newkey rsa:2048 \
        -sha256 \
        -days 365 \
        -nodes \
        -keyout /certs/localhost.key \
        -out /certs/localhost.crt \
        -subj '/CN=localhost' \
        -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'"

echo ""
echo "Certificate generated successfully:"
echo "  $CERT_DIR/localhost.crt"
echo "  $CERT_DIR/localhost.key"