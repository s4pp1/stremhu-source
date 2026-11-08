"""cr15a-after-v4 harness: load app.config (the production server always has it loaded) before the unchanged
probe.py, identically on the before and after side. sys.argv is passed through unchanged."""
import runpy

import app.config  # noqa: F401

runpy.run_path('/fixture/probe.py', run_name='__main__')
