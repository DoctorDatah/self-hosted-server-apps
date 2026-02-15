# Local Validation (Infisical)

Validate Infisical access using local config values.

## Config file (macOS local)
Edit:
`/Users/malikqayyum/self-hosted-server-apps/VMs/Infisical Variables/local_validation/infisical.local.env`

Example:
```bash
INFISICAL_TOKEN=your_service_token_here
INFISICAL_PROJECT_ID=your_project_id_here
INFISICAL_ENV=production
# INFISICAL_API_URL=https://your-infisical-domain/api
```

## Commands (macOS local)
Open the config file:
```bash
open "/Users/malikqayyum/self-hosted-server-apps/VMs/Infisical Variables/local_validation/infisical.local.env"
```
Or edit in terminal:
```bash
nano "/Users/malikqayyum/self-hosted-server-apps/VMs/Infisical Variables/local_validation/infisical.local.env"
```
Note: Do not use backticks around the path. Backticks try to execute the file as a command.

## Run on macOS
```bash
"/Users/malikqayyum/self-hosted-server-apps/VMs/Infisical Variables/local_validation/validate_infisical_access_specified_folder.sh"
```

## Run (all folders)
```bash
"/Users/malikqayyum/self-hosted-server-apps/VMs/Infisical Variables/local_validation/validate_infisical_access_all_needed_folder.sh"
```

## More help
- See `CLI based validation/TROUBLESHOOTING.md` for macOS command-line checks.
