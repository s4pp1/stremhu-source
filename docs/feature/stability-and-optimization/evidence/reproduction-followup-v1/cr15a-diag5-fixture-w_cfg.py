import app.config  # diagnostic: production module set preloaded (as cr15a-after-v4)
import runpy
runpy.run_path('/diag/probe_retention.py', run_name='__main__')
