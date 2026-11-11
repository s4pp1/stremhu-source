import app.config  # diagnostic: production module set preloaded
import runpy
runpy.run_path('/diag/probe_small.py', run_name='__main__')
