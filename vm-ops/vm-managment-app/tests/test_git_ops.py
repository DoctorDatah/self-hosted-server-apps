#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import git_ops


class GitOpsTest(unittest.TestCase):
    def _run(self, root: Path, args):
        proc = subprocess.run(args, cwd=root, check=True, capture_output=True, text=True)
        return proc.stdout.strip()

    def _seed_repo(self, root: Path) -> None:
        self._run(root, ["git", "init"]) 
        self._run(root, ["git", "config", "user.email", "test@example.com"])
        self._run(root, ["git", "config", "user.name", "VM Config Test"])

        cfg = root / "vm-configs"
        cfg.mkdir(parents=True, exist_ok=True)
        for name, payload in [
            ("vm-machines.yaml", {"machines": {}, "groups": {}}),
            ("vm-operations.yaml", {"operations": {}}),
            ("vm-env-rules.yaml", {"rules": {}}),
        ]:
            (cfg / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

        self._run(root, ["git", "add", "."])
        self._run(root, ["git", "commit", "-m", "init"])

    def test_prepare_commit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)

            machines = root / "vm-configs" / "vm-machines.yaml"
            machines.write_text(
                json.dumps(
                    {
                        "machines": {
                            "m1": {
                                "env": "stage",
                                "enabled_setups": ["vm_install"],
                                "exec_mode": "local",
                            }
                        },
                        "groups": {},
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = git_ops.prepare_commit(
                root,
                tracked_files=[
                    "vm-configs/vm-machines.yaml",
                    "vm-configs/vm-operations.yaml",
                    "vm-configs/vm-env-rules.yaml",
                ],
            )

            self.assertTrue(result["branch"].startswith("config_update/"))
            self.assertTrue(result["commit_sha"])
            self.assertIn("vm-configs/vm-machines.yaml", result["changed_files"])

    def test_switch_and_push_branch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            root.mkdir(parents=True, exist_ok=True)
            self._seed_repo(root)

            remote = Path(td) / "remote.git"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True, text=True)
            self._run(root, ["git", "remote", "add", "origin", str(remote)])

            initial_branch = git_ops.current_branch(root)
            target_branch = "config_update/March-07-2026--12-34-PM"
            switched = git_ops.switch_branch(root, target_branch)
            self.assertEqual(switched["branch"], target_branch)
            # UI target branch should not checkout/switch the main local branch.
            self.assertEqual(git_ops.current_branch(root), initial_branch)

            pushed = git_ops.push_branch(root, branch_name=target_branch, remote_name="origin", set_upstream=True)
            self.assertEqual(pushed["branch"], target_branch)
            self.assertEqual(pushed["remote"], "origin")

            remote_heads = subprocess.run(
                ["git", "ls-remote", "--heads", str(remote), target_branch],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertTrue(remote_heads)

    def test_push_requires_explicit_branch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)
            with self.assertRaises(git_ops.GitOpsError):
                git_ops.push_branch(root, branch_name="", remote_name="origin", set_upstream=True)

    def test_prepare_commit_reuses_existing_related_branch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)

            existing = "config_update/March-07-2026--12-00-PM"
            self._run(root, ["git", "branch", existing])

            machines = root / "vm-configs" / "vm-machines.yaml"
            machines.write_text(
                json.dumps({"machines": {"m2": {"env": "dev"}}, "groups": {}}, indent=2) + "\n",
                encoding="utf-8",
            )

            result = git_ops.prepare_commit(
                root,
                tracked_files=[
                    "vm-configs/vm-machines.yaml",
                    "vm-configs/vm-operations.yaml",
                    "vm-configs/vm-env-rules.yaml",
                ],
                preferred_branch="",
                fallback_tz="UTC",
            )
            self.assertEqual(result["branch"], existing)

    def test_resolve_target_branch_rejects_polluted_explicit_branch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)
            base_branch = self._run(root, ["git", "rev-parse", "--abbrev-ref", "HEAD"])
            branch = "config_update/March-07-2026--12-00-PM"
            self._run(root, ["git", "checkout", "-b", branch])
            (root / "README.md").write_text("non-config-change\n", encoding="utf-8")
            self._run(root, ["git", "add", "README.md"])
            self._run(root, ["git", "commit", "-m", "pollute branch"])
            self._run(root, ["git", "checkout", base_branch])

            with self.assertRaises(git_ops.GitOpsError) as exc:
                git_ops.resolve_target_branch(
                    root,
                    explicit_branch=branch,
                    preferred_branch="",
                    fallback_tz="UTC",
                )
            self.assertIn("contains non-config history", str(exc.exception))

    def test_resolve_target_branch_skips_polluted_related_branch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)
            base_branch = self._run(root, ["git", "rev-parse", "--abbrev-ref", "HEAD"])
            branch = "config_update/March-07-2026--12-00-PM"
            self._run(root, ["git", "checkout", "-b", branch])
            (root / "README.md").write_text("non-config-change\n", encoding="utf-8")
            self._run(root, ["git", "add", "README.md"])
            self._run(root, ["git", "commit", "-m", "pollute branch"])
            self._run(root, ["git", "checkout", base_branch])

            resolved, exists = git_ops.resolve_target_branch(
                root,
                explicit_branch="",
                preferred_branch="",
                fallback_tz="UTC",
            )
            self.assertFalse(exists)
            self.assertTrue(resolved.startswith("config_update/"))
            self.assertNotEqual(resolved, branch)

    def test_list_related_open_prs(self) -> None:
        payload = json.dumps(
            [
                {
                    "number": 10,
                    "title": "config update",
                    "headRefName": "config_update/March-07-2026--12-00-PM",
                    "baseRefName": "main",
                    "url": "https://example/pr/10",
                    "updatedAt": "2026-03-07T01:00:00Z",
                    "author": {"login": "hassan"},
                },
                {
                    "number": 11,
                    "title": "feature xyz",
                    "headRefName": "feature/xyz",
                    "baseRefName": "main",
                    "url": "https://example/pr/11",
                    "updatedAt": "2026-03-07T01:00:00Z",
                    "author": {"login": "hassan"},
                },
            ]
        )
        fake_proc = subprocess.CompletedProcess(args=["gh"], returncode=0, stdout=payload, stderr="")
        with mock.patch("app.features.config_management.services.git_ops._run_gh", return_value=fake_proc):
            rows = git_ops.list_open_prs(Path("."), related_only=True)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["number"], 10)

    def test_create_pr_uses_gh(self) -> None:
        fake_proc = subprocess.CompletedProcess(
            args=["gh"],
            returncode=0,
            stdout="https://github.com/org/repo/pull/123\n",
            stderr="",
        )
        with mock.patch("app.features.config_management.services.git_ops._run_gh", return_value=fake_proc):
            pr = git_ops.create_pr(
                Path("."),
                head_branch="config_update/March-07-2026--12-00-PM",
                base_branch="main",
                title="chore: config",
                body="details",
                use_fill=True,
            )
            self.assertIn("/pull/123", pr["url"])

    def test_default_branch_name_format(self) -> None:
        branch = git_ops.default_branch_name("UTC")
        self.assertTrue(branch.startswith("config_update/"))
        self.assertIn("--", branch)
        self.assertNotIn(":", branch)

    def test_switch_rejects_non_config_branch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)
            with self.assertRaises(git_ops.GitOpsError):
                git_ops.switch_branch(root, "main")

    def test_list_open_prs_reports_missing_gh(self) -> None:
        with mock.patch(
            "app.features.config_management.services.git_ops.subprocess.run",
            side_effect=FileNotFoundError("gh"),
        ):
            with self.assertRaises(git_ops.GitOpsError) as exc:
                git_ops.list_open_prs(Path("."), related_only=True)
            self.assertIn("not installed", str(exc.exception).lower())

    def test_delete_branch_removes_local_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)
            branch = "config_update/March-07-2026--12-45-PM"
            self._run(root, ["git", "branch", branch])
            result = git_ops.delete_branch(root, branch_name=branch, delete_local=True, delete_remote=False)
            self.assertTrue(result["local_deleted"])
            self.assertFalse(result["remote_deleted"])

    def test_close_pr_uses_gh(self) -> None:
        fake_proc = subprocess.CompletedProcess(args=["gh"], returncode=0, stdout="closed", stderr="")
        with mock.patch("app.features.config_management.services.git_ops._run_gh", return_value=fake_proc):
            result = git_ops.close_pr(Path("."), pr_number=42, delete_branch=True)
            self.assertEqual(result["number"], 42)
            self.assertTrue(result["delete_branch"])

    def test_related_branches_include_github_url(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)
            self._run(root, ["git", "remote", "add", "origin", "https://github.com/example-org/example-repo.git"])
            branch = "config_update/March-07-2026--12-45-PM"
            self._run(root, ["git", "branch", branch])

            rows = git_ops.list_related_branches(root, preferred_branch="", limit=100, remote_name="origin")
            match = [row for row in rows if row.get("branch") == branch]
            self.assertEqual(len(match), 1)
            self.assertIn("https://github.com/example-org/example-repo/tree/config_update/", match[0].get("github_url", ""))

    def test_list_tracked_sensitive_files_detects_app_data(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)
            app_data = root / "vm-managment-app" / "app-data"
            app_data.mkdir(parents=True, exist_ok=True)
            token_file = app_data / "oauth-token.json"
            token_file.write_text('{"token":"secret"}\n', encoding="utf-8")
            self._run(root, ["git", "add", str(token_file.relative_to(root))])
            tracked = git_ops.list_tracked_sensitive_files(root)
            self.assertIn("vm-managment-app/app-data/oauth-token.json", tracked)

    def test_prepare_commit_blocks_when_sensitive_files_tracked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)
            app_data = root / "vm-managment-app" / "app-data"
            app_data.mkdir(parents=True, exist_ok=True)
            token_file = app_data / "oauth-token.json"
            token_file.write_text('{"token":"secret"}\n', encoding="utf-8")
            self._run(root, ["git", "add", str(token_file.relative_to(root))])
            with self.assertRaises(git_ops.GitOpsError) as exc:
                git_ops.prepare_commit(
                    root,
                    tracked_files=[
                        "vm-configs/vm-machines.yaml",
                        "vm-configs/vm-operations.yaml",
                        "vm-configs/vm-env-rules.yaml",
                    ],
                )
            self.assertIn("Sensitive local app data is tracked by git", str(exc.exception))

    def test_github_connection_status_not_installed(self) -> None:
        with mock.patch("app.features.config_management.services.git_ops._resolve_gh_exec", return_value=""):
            status = git_ops.github_connection_status(Path("."))
            self.assertFalse(status["available"])
            self.assertFalse(status["authenticated"])

    def test_github_connection_status_connected(self) -> None:
        fake_proc = subprocess.CompletedProcess(
            args=["gh"],
            returncode=0,
            stdout="",
            stderr="Logged in to github.com as hassan (token)\n",
        )
        with mock.patch("app.features.config_management.services.git_ops._resolve_gh_exec", return_value="/usr/local/bin/gh"):
            with mock.patch("app.features.config_management.services.git_ops.subprocess.run", return_value=fake_proc):
                status = git_ops.github_connection_status(Path("."))
                self.assertTrue(status["available"])
                self.assertTrue(status["authenticated"])
                self.assertEqual(status["username"], "hassan")

    def test_github_connection_status_fallbacks_to_token_and_user(self) -> None:
        status_proc = subprocess.CompletedProcess(
            args=["gh"],
            returncode=1,
            stdout="",
            stderr="not logged in",
        )
        token_proc = subprocess.CompletedProcess(
            args=["gh"],
            returncode=0,
            stdout="gho_example_token\n",
            stderr="",
        )
        user_proc = subprocess.CompletedProcess(
            args=["gh"],
            returncode=0,
            stdout="DoctorDatah\n",
            stderr="",
        )
        with mock.patch("app.features.config_management.services.git_ops._resolve_gh_exec", return_value="/usr/local/bin/gh"):
            with mock.patch(
                "app.features.config_management.services.git_ops.subprocess.run",
                side_effect=[status_proc, token_proc, user_proc],
            ):
                status = git_ops.github_connection_status(Path("."))
                self.assertTrue(status["available"])
                self.assertTrue(status["authenticated"])
                self.assertEqual(status["username"], "DoctorDatah")

    def test_connect_github_web_uses_cli(self) -> None:
        fake_popen = mock.Mock()
        fake_popen.pid = 9999
        with mock.patch("app.features.config_management.services.git_ops._resolve_gh_exec", return_value="/usr/local/bin/gh"):
            with mock.patch(
                "app.features.config_management.services.git_ops.subprocess.Popen",
                return_value=fake_popen,
            ):
                with mock.patch(
                    "app.features.config_management.services.git_ops._poll_clipboard_for_device_code",
                    return_value="ABCD-EFGH",
                ):
                    out = git_ops.connect_github_web(Path("."))
                    self.assertTrue(out["ok"])
                    self.assertEqual(out["pid"], 9999)
                    self.assertEqual(out["device_code"], "ABCD-EFGH")

    def test_connect_github_web_falls_back_to_clipboard_code(self) -> None:
        fake_popen = mock.Mock()
        fake_popen.pid = 9999
        with mock.patch("app.features.config_management.services.git_ops._resolve_gh_exec", return_value="/usr/local/bin/gh"):
            with mock.patch(
                "app.features.config_management.services.git_ops.subprocess.Popen",
                return_value=fake_popen,
            ):
                with mock.patch(
                    "app.features.config_management.services.git_ops._poll_clipboard_for_device_code",
                    return_value="WXYZ-1234",
                ):
                    out = git_ops.connect_github_web(Path("."))
                    self.assertEqual(out["device_code"], "WXYZ-1234")

    def test_disconnect_github_uses_cli(self) -> None:
        fake_proc = subprocess.CompletedProcess(args=["gh"], returncode=0, stdout="ok", stderr="")
        with mock.patch(
            "app.features.config_management.services.git_ops.github_connection_status",
            return_value={"available": True, "authenticated": True, "username": "hassan"},
        ):
            with mock.patch("app.features.config_management.services.git_ops._run_gh", return_value=fake_proc):
                out = git_ops.disconnect_github(Path("."))
                self.assertTrue(out["ok"])


if __name__ == "__main__":
    unittest.main()
