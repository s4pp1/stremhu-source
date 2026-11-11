"""Offline Range parser baseline, including previously unhandled inputs."""

import json
import statistics
import time

from fastapi import HTTPException

from app.modules.stream import service as stream_service_module

parse_range_header = getattr(stream_service_module, "parse_range_header", None)
if parse_range_header is None:
    # Reviewed upstream API: this pure legacy method does not read instance state.
    parse_range_header = object.__new__(stream_service_module.StreamService)._parse_range_header


rows = []
for name, header in [
    ("normal", "bytes=0-99"),
    ("latin1-digit", "bytes=\u00b2-"),
    ("long-start", "bytes=" + "9" * 5000 + "-"),
    ("long-end", "bytes=0-" + "9" * 5000),
    ("long-suffix", "bytes=-" + "9" * 5000),
    ("leading-zero", "bytes=" + "0" * 5000 + "10-99"),
]:
    samples, outcomes = [], {}
    for _ in range(1000):
        started = time.perf_counter_ns()
        try:
            result = parse_range_header(1000, header)
            outcome = f"range:{result.start_byte}:{result.end_byte}"
        except HTTPException as error:
            outcome = f"http:{error.status_code}"
        except Exception as error:
            outcome = type(error).__name__
        samples.append((time.perf_counter_ns() - started) / 1e6)
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    ordered = sorted(samples)
    rows.append(dict(workload=name, concurrency=1, samples_ms=samples, p50_ms=statistics.median(samples), p95_ms=ordered[949], p99_ms=ordered[989], outcomes=outcomes, errors=[]))
print(json.dumps(dict(fixture="range-ASCII-latin1-5000-digit-v1", rows=rows)))
