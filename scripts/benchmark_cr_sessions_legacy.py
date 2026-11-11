"""Run the identical session workload on images predating the rate limiter.

The old application has no limiter or injectable admission clock. The shim is
only for the fixture's logical-minute assignment; it does not change old auth,
password, cookie or database behavior. Rate-limit compatibility is N/A here.
"""

import runpy
import sys
from types import ModuleType

clock_fixture = ModuleType("app.common.auth_rate_limit")
clock_fixture.AuthRateLimiter = lambda **kwargs: None
sys.modules[clock_fixture.__name__] = clock_fixture
runpy.run_path("/fixture/sessions.py", run_name="__main__")
