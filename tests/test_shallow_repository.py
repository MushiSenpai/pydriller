# Copyright 2018 Davide Spadini
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging

import pytest
from git import Repo
from git.exc import GitCommandError
from git.objects.commit import Commit as GitCommit

from pydriller import Git, ShallowRepositoryError


@pytest.fixture
def repos(tmp_path):
    """Build a 3-commit repository and a --depth 1 clone of it."""
    source = tmp_path / "source"
    source.mkdir()
    repo = Repo.init(source)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "test")
        cw.set_value("user", "email", "test@test.test")
    for i in range(3):
        (source / "file.txt").write_text(f"line {i}\n")
        repo.index.add(["file.txt"])
        repo.index.commit(f"commit {i}")
    repo.close()

    shallow = tmp_path / "shallow"
    Repo.clone_from(source.as_uri(), shallow, depth=1).close()
    return source, shallow


def test_shallow_clone_raises_informative_error(repos):
    _, shallow = repos
    gr = Git(str(shallow))
    commit = gr.get_head()

    with pytest.raises(ShallowRepositoryError) as exc_info:
        _ = commit.modified_files

    message = str(exc_info.value)
    assert "shallow clone" in message
    assert "git fetch --unshallow" in message
    assert commit.hash in message
    gr.clear()


def test_shallow_clone_warns_when_opened(repos, caplog):
    _, shallow = repos
    with caplog.at_level(logging.WARNING):
        gr = Git(str(shallow))
        gr.get_head()

    assert any("shallow clone" in record.message for record in caplog.records)
    gr.clear()


def test_complete_clone_is_not_affected(repos, caplog):
    source, _ = repos
    with caplog.at_level(logging.WARNING):
        gr = Git(str(source))
        modified_files = gr.get_head().modified_files

    assert [mod.filename for mod in modified_files] == ["file.txt"]
    assert not any("shallow clone" in record.message for record in caplog.records)
    gr.clear()


def test_other_git_errors_are_not_relabelled(repos, monkeypatch):
    """A git failure in a complete clone must surface unchanged."""
    source, _ = repos
    gr = Git(str(source))
    commit = gr.get_head()

    def boom(*args, **kwargs):
        raise GitCommandError(["git", "diff-tree"], 128, b"fatal: something else entirely")

    monkeypatch.setattr(GitCommit, "diff", boom)

    with pytest.raises(GitCommandError) as exc_info:
        _ = commit.modified_files

    assert not isinstance(exc_info.value, ShallowRepositoryError)
    assert "something else entirely" in str(exc_info.value)
    gr.clear()
