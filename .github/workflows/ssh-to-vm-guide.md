# SSH from GitHub Actions to VM

## Summary
- **Goal:** Let GitHub Actions connect to the VM over SSH for deploy tasks.
- **Scope:** GitHub + VM setup; no app-specific commands here.

## Preconditions
- VM is reachable from the internet.
- You can SSH to the VM from your local machine.
- You have admin access to the GitHub repo settings.

## Generate a Deploy Key (Local)
```bash
ssh-keygen -t ed25519 -C "gh-actions-n8n" -f ~/.ssh/gh-actions-n8n
```
This creates:
- Private key: `~/.ssh/gh-actions-n8n`
- Public key: `~/.ssh/gh-actions-n8n.pub`

## Add Public Key to VM
```bash
ssh <your-user>@<your-vm-ip>
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat >> ~/.ssh/authorized_keys
# paste the public key from ~/.ssh/gh-actions-n8n.pub, then Ctrl+D
chmod 600 ~/.ssh/authorized_keys
```

## Add Secrets in GitHub
Repo → Settings → Secrets and variables → Actions → New repository secret:
- `SSH_HOST` = VM IP or hostname
- `SSH_USER` = SSH username (e.g., `malik`)
- `SSH_PORT` = `22` (or your custom port)
- `SSH_PRIVATE_KEY` = contents of `~/.ssh/gh-actions-n8n`

## Add to Workflow (example)
Use this inside a job in `.github/workflows/deploy.yml`:
```yaml
    - name: Add SSH key
      run: |
        mkdir -p ~/.ssh
        chmod 700 ~/.ssh
        echo "${{ secrets.SSH_PRIVATE_KEY }}" > ~/.ssh/id_ed25519
        chmod 600 ~/.ssh/id_ed25519
        ssh-keyscan -p "${{ secrets.SSH_PORT }}" "${{ secrets.SSH_HOST }}" >> ~/.ssh/known_hosts

    - name: Test SSH
      run: |
        ssh -p "${{ secrets.SSH_PORT }}" "${{ secrets.SSH_USER }}@${{ secrets.SSH_HOST }}" "hostname && whoami"
```

## Notes
- If you rotate keys, update both the VM `authorized_keys` and GitHub secret.
- Use a dedicated key for CI (do not reuse your personal SSH key).

