# pylint: disable=C0111
from .domain.commit import Commit, ModifiedFile, ModificationType, ShallowRepositoryError # noqa
from .repository import Repository, Git    # noqa

__version__ = "2.12"
