# Local Development Certificates

This directory is used for the self-signed HTTPS certificate and private key required by the local Docker/Nginx setup.

The generated files are:

localhost.crt
localhost.key

For Windows:
    From the root directory, run:
        .\scripts\generate-dev-cert.ps1
    If PowerShell blocks running scipts, temporarily allow scripts using:
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    Then rerun the first line.

For MaxOS/Linux:
    From the root directory, run:
        ./scripts/generate-dev-cert.sh
    If necessary, make the script executable first using:
        chmod +x scripts/generate-dev-cert.sh
    Then rerun the first line.

After generation, your directory should look like:
    certs/
    ├── localhost.crt
    ├── localhost.key
    └── README.md

After generating the certificate, startup GopherGPT with:
    docker compose up --build

The certificate is self-signed, so your browser will display a security warning when visiting:
    https://localhost