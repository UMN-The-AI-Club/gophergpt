$ErrorActionPreference = "Stop"

# Find the root of the GopherGPT repository.
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# Create the certs directory if it does not already exist.
$certDir = Join-Path $repoRoot "certs"
New-Item -ItemType Directory -Force -Path $certDir | Out-Null

Write-Host "Generating self-signed HTTPS certificate for localhost..."

docker run --rm `
    -v "${certDir}:/certs" `
    alpine sh -c "apk add --no-cache openssl && openssl req -x509 -newkey rsa:2048 -sha256 -days 365 -nodes -keyout /certs/localhost.key -out /certs/localhost.crt -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'"

if ($LASTEXITCODE -ne 0) {
    throw "Failed to generate the development HTTPS certificate."
}

Write-Host ""
Write-Host "Certificate generated successfully:"
Write-Host "  $certDir\localhost.crt"
Write-Host "  $certDir\localhost.key"