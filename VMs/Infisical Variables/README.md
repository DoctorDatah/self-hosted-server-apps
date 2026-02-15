# Infisical Variables (VM)

Fetch secrets from Infisical and write them to a `.env` file under `VMs/`.

## High-level explanation
This script connects to Infisical using the token you provide, exports secrets from either the entire project (including subfolders) or a specific folder, and writes them into `VMs/.env` so other VM scripts can load them as environment variables.

## Prerequisites
- Infisical CLI installed on the VM.
- Network access to Infisical.

## Run on the VM
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Infisical Variables/fetch_infisical_env.sh"
```
To show extra step-by-step detail:
```bash
DEBUG=1 "/home/malik/self-hosted-server-apps/VMs/Infisical Variables/fetch_infisical_env.sh"
```

## Run on macOS (local)
```bash
"/Users/malikqayyum/self-hosted-server-apps/VMs/Infisical Variables/fetch_infisical_env.sh"
```
To show extra step-by-step detail:
```bash
DEBUG=1 "/Users/malikqayyum/self-hosted-server-apps/VMs/Infisical Variables/fetch_infisical_env.sh"
```

## Validate access (macOS)
Edit the local config:
`/Users/malikqayyum/self-hosted-server-apps/VMs/Infisical Variables/local_validation/infisical.local.env`

Run the validator:
```bash
"/Users/malikqayyum/self-hosted-server-apps/VMs/Infisical Variables/local_validation/validate_infisical_access.sh"
```

## What it does
- Prompts for Infisical Project ID and token.
- Asks whether to fetch all variables from `/` or a specific folder.
- Lists available folders when you choose a specific folder.
- Writes `VMs/.env` and locks it to `600` permissions.
- Prints the secret names after export.

## Output
- `.env` is created at:
  `/home/malik/self-hosted-server-apps/VMs/.env`

## Notes
- Default environment is `production` (you can override when prompted).
- Keep the token private.
- The script uses the root path `/` to fetch all secrets available to the token.
