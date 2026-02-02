# Coolify: fetch a private GitHub repo (SSH key setup)

Use this when your Coolify app points to a private GitHub repo and you need to add the deploy key.

---

## 1) Generate a deploy key in Coolify
In Coolify UI:
1) `Sources -> GitHub -> Manage` (or `Settings -> Sources` depending on version)
2) Create or select the GitHub source used by your app
3) Copy the **public key** shown (starts with `ssh-ed25519`)

If you do not see a key, create one in the same screen and then copy its public key.

---

## 2) Add the key to GitHub (repo deploy key)
In GitHub (for the target repo):
1) `Repo -> Settings -> Deploy keys -> Add deploy key`
2) Title: `coolify`
3) Key: paste the public key from Coolify
4) Enable **Allow write access** only if Coolify needs to push tags/commits (usually not needed)

---

## 3) Use the SSH repo URL in Coolify
In Coolify when adding the application:
- Use the SSH URL (not HTTPS)
  - Example: `git@github.com:ORG/REPO.git`
- Select the same GitHub source/key you just created

---

## 4) Validate
In Coolify:
- Re-deploy the app
- If the repo still fails to clone, check:
  - The app uses the SSH URL
  - The deploy key is added to the correct repo
  - The source/key selected in Coolify matches the key you added

---

## Common issues
- **Permission denied (publickey)**: wrong key added or wrong repo.
- **Repo not found**: using HTTPS URL instead of SSH.
- **Multiple repos**: you must add the key to each repo that Coolify needs.
