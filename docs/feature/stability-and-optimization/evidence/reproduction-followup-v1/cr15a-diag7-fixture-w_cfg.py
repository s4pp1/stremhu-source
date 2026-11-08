import app.config  # diagnostic: production module set preloaded (as cr15a-after-v4)
import runpy
runpy.run_path('/diag/probe_faults.py', run_name='__main__')
