"""
EPC Module Hooks

Re-exports everything from the root-level app hooks (epc_modules/hooks.py)
so that Frappe's `epc_modules.hooks` resolution picks up the real hooks.
"""
import os, importlib.util

# The root hooks.py is one level up from this file's parent directory
# this file: epc_modules/epc_modules/hooks.py
# root hooks: epc_modules/hooks.py
_parent_dir = os.path.dirname(os.path.dirname(__file__))
_hook_path = os.path.join(_parent_dir, "hooks.py")

_spec = importlib.util.spec_from_file_location("_app_hooks", _hook_path)
_root_hooks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_hooks)

for _n in dir(_root_hooks):
    if not _n.startswith("_"):
        globals()[_n] = getattr(_root_hooks, _n)