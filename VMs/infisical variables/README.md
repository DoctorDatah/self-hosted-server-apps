# Infisical Variables (VM)

Fetch secrets from Infisical and write them to a `.env` file under `VMs/`.

## High-level explanation
This script connects to Infisical using the token you provide, exports secrets from either the entire project (including subfolders) or a specific folder, and writes them into `VMs/.env` so other VM scripts can load them as environment variables.

## Prerequisites
- Infisical CLI installed on the VM.
- Network access to Infisical.

## Run on the VM
```bash
"/home/malik/self-hosted-server-apps/VMs/Infisical Variables/fetch_infisical_env.sh"
```
Or from inside the folder:
```bash
cd "/home/malik/self-hosted-server-apps/VMs/Infisical Variables"
./fetch_infisical_env.sh
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
