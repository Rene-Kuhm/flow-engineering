"""DEPRECATED back-compat shim. Use ``flow_engineering.cli.archive`` instead.

The original ``cli/rotation.py`` was a 161-LOC module that defined the
``flow archive rotate`` Click command + its helpers. v1.3-cli-split
Slice 8/8 (FINAL) renamed the module to ``cli/archive.py`` (it now
hosts the full ``flow archive`` group: ``rotate`` + ``change``). This
file is preserved as a 1-line back-compat shim so any external caller
of ``from flow_engineering.cli.rotation import X`` continues to work.

The shim re-exports the three public names from ``cli.archive``:
``rotate_cmd`` (the Click command), ``_candidate_entries`` and
``_entry_mtime`` (the helper functions used by
``tests/unit/test_cli_rotation.py``). It ALSO re-exports the stdlib /
third-party names that the original module's body imported at module
level (``hashlib``, ``json``, ``subprocess``, ``UTC``, ``datetime``,
``Path``, ``Any``, ``click``, ``yaml``). Tests patch
``flow_engineering.cli.rotation.subprocess.run`` via the string-form
``monkeypatch.setattr`` API; that path resolution walks the module
namespace and requires ``subprocess`` to be an attribute of this
module. Re-exporting the stdlib bindings preserves that test seam
without forcing the test to change.
"""
from flow_engineering.cli.archive import (  # noqa: F401
    rotate_cmd,
    _candidate_entries,
    _entry_mtime,
)
from flow_engineering.cli.archive import (  # noqa: F401
    hashlib,
    json,
    subprocess,
)
from flow_engineering.cli.archive import UTC, datetime  # noqa: F401
from flow_engineering.cli.archive import Path  # noqa: F401
from flow_engineering.cli.archive import Any  # noqa: F401
import click  # noqa: F401
import yaml  # noqa: F401