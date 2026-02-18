# SSH to VM from GitHub Actions

This guide shows how to let a GitHub Actions workflow connect to your VM over SSH.

## 1) Prepare the VM

1. Ensure SSH is installed and running on the VM.
2. Create a deploy user (recommended, not root), and add it to required groups.
3. Allow the VM to accept SSH connections from GitHub Actions (public internet) or use a VPN/tunnel.
4. Open the SSH port (default `22`) in your firewall/security group.

## 2) Create an SSH keypair for GitHub Actions

Run these on your local machine (not the VM):

```bash
ssh-keygen -t ed25519 -C "github-actions" -f ./gh_actions_vm
```

This creates:
- Private key: `./gh_actions_vm`
- Public key: `./gh_actions_vm.pub`

## 3) Add the public key to the VM

On the VM, add the public key to the deploy user:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat >> ~/.ssh/authorized_keys <<'EOF'
<PASTE CONTENTS OF gh_actions_vm.pub HERE>
EOF
chmod 600 ~/.ssh/authorized_keys
```

## 4) Add secrets to GitHub

In your GitHub repo Settings → Secrets and variables → Actions:

- `VM_HOST`: VM public IP or DNS
- `VM_USER`: SSH username (deploy user)
- `VM_SSH_KEY`: **private key** contents from `gh_actions_vm`
- `VM_SSH_PORT`: optional (default `22`)

Optional hardening:
- `VM_KNOWN_HOSTS`: output of `ssh-keyscan -p 22 <host>`

## 5) Example GitHub Actions step

Use an SSH action (simple):

```yaml
- name: SSH to VM
  uses: appleboy/ssh-action@v1.0.3
  with:
    host: ${{ secrets.VM_HOST }}
    username: ${{ secrets.VM_USER }}
    key: ${{ secrets.VM_SSH_KEY }}
    port: ${{ secrets.VM_SSH_PORT }}
    script: |
      uname -a
      whoami
```

Or use native SSH:

```yaml
- name: Set up SSH
  run: |
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    echo "${{ secrets.VM_SSH_KEY }}" > ~/.ssh/id_ed25519
    chmod 600 ~/.ssh/id_ed25519
    ssh-keyscan -p ${VM_SSH_PORT:-22} ${{ secrets.VM_HOST }} >> ~/.ssh/known_hosts

- name: SSH to VM
  run: |
    ssh -p ${VM_SSH_PORT:-22} ${{ secrets.VM_USER }}@${{ secrets.VM_HOST }} "uname -a && whoami"
```

## 6) Common issues

- **Permission denied (publickey)**: key mismatch or wrong user.
- **Connection timed out**: firewall/port closed, wrong IP, VM not reachable.
- **Host key verification failed**: ensure `known_hosts` is set.

## 7) Recommendation

Use a dedicated deploy user and restrict its permissions. Avoid SSHing as root unless required.
