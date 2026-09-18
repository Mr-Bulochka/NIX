"""Code knowledge modules: data-driven packs that teach NIX how
blocks, operations and generation work in a concrete language.

A module is a plain-data folder (no code):  module.json, blocks.json,
ops.json, gen/*.tmpl, probe.json.  Bundled modules ship inside
nix/modules/bundled/<id>/.  User modules are looked up in
~/.nix/modules/<id>/ and win over bundled ones.
"""

from .loader import (
    CodeModule,
    all_modules,
    BUNDLED_DIR,
    USER_MODULES_DIR,
    module_for_file,
    module_for_ext,
    load_module,
    predict_priority_language,
    set_enabled_modules,
    is_module_enabled,
)
from .engine import (
    Block,
    find_block_at_line,
    scan_blocks,
    apply_wrap,
    render_template,
)

__all__ = [
    "CodeModule",
    "all_modules",
    "BUNDLED_DIR",
    "USER_MODULES_DIR",
    "module_for_file",
    "module_for_ext",
    "load_module",
    "predict_priority_language",
    "set_enabled_modules",
    "is_module_enabled",
    "Block",
    "find_block_at_line",
    "scan_blocks",
    "apply_wrap",
    "render_template",
]