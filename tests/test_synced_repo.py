from pathlib import Path
from unittest import mock

import pytest

from nf_core.modules.modules_repo import ModulesRepo
from nf_core.pipelines.download.workflow_repo import WorkflowRepo
from nf_core.synced_repo import SyncedRepo


class DummyRepo(SyncedRepo):
    def setup_local_repo(self, remote_url, branch, hide_progress):
        pass


def test_get_remote_branches_ignores_empty_lines():
    git_client = mock.Mock()
    git_client.ls_remote.return_value = "sha1\trefs/heads/main\n\nsha2\trefs/heads/dev\n"
    with mock.patch("git.Git", return_value=git_client):
        branches = SyncedRepo.get_remote_branches("https://example.org/repo.git")
    assert branches == {"main", "dev"}


def test_get_avail_components_invalid_type_raises():
    repo = DummyRepo()
    repo.repo = mock.Mock()
    repo.modules_dir = Path("/tmp/modules")
    repo.subworkflows_dir = Path("/tmp/subworkflows")
    with pytest.raises(ValueError, match="Invalid component type"):
        repo.get_avail_components("invalid-type", checkout=False)


def test_open_or_clone_repo_clones_missing_repo(tmp_path):
    repo = DummyRepo()
    repo.fullname = "nf-core/modules"
    repo.local_repo_dir = tmp_path / "missing-repo"
    repo.remote_url = "https://example.org/repo.git"

    with mock.patch.object(repo, "_clone_repo") as clone_mock:
        cloned = repo._open_or_clone_repo("https://example.org/repo.git", hide_progress=True)

    clone_mock.assert_called_once()
    assert cloned is True


def test_open_or_clone_repo_fetches_existing_repo(tmp_path):
    repo = DummyRepo()
    repo.fullname = "nf-core/modules"
    repo.local_repo_dir = tmp_path / "existing-repo"
    repo.local_repo_dir.mkdir()
    repo.remote_url = "https://example.org/repo.git"

    with (
        mock.patch("git.Repo", return_value=mock.Mock()) as repo_ctor,
        mock.patch.object(repo, "_fetch_repo") as fetch_mock,
        mock.patch.object(SyncedRepo, "local_repo_synced", return_value=False),
    ):
        cloned = repo._open_or_clone_repo("https://example.org/repo.git", hide_progress=True)

    repo_ctor.assert_called_once_with(repo.local_repo_dir)
    fetch_mock.assert_called_once()
    assert cloned is False


def test_modules_repo_setup_local_repo_uses_shared_bootstrap(tmp_path):
    repo = ModulesRepo.__new__(ModulesRepo)
    repo.fullname = "nf-core/modules"
    repo.remote_url = "https://example.org/repo.git"
    repo.repo = mock.Mock()
    repo.repo.active_branch.tracking_branch.return_value = mock.Mock(name="origin/master")

    with (
        mock.patch.object(repo, "_open_or_clone_repo", return_value=False) as bootstrap_mock,
        mock.patch.object(repo, "setup_branch") as setup_branch_mock,
    ):
        ModulesRepo.setup_local_repo(repo, "https://example.org/repo.git", "master", hide_progress=True, in_cache=False)

    bootstrap_mock.assert_called_once_with(
        "https://example.org/repo.git",
        True,
        skip_pull=ModulesRepo.no_pull_global,
    )
    setup_branch_mock.assert_called_once_with("master")
    repo.repo.git.merge.assert_called_once()


def test_workflow_repo_setup_local_repo_uses_shared_bootstrap(tmp_path):
    repo = WorkflowRepo.__new__(WorkflowRepo)
    repo.fullname = "nf-core/rnaseq"
    repo.remote_url = "https://example.org/repo.git"
    repo.hide_progress = True

    with mock.patch.object(repo, "_open_or_clone_repo") as bootstrap_mock:
        WorkflowRepo.setup_local_repo(repo, "https://example.org/repo.git", location=tmp_path, in_cache=False)

    bootstrap_mock.assert_called_once_with(
        "https://example.org/repo.git",
        True,
        skip_pull=repo.no_pull_global,
    )
