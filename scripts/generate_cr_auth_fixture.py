"""A fixed synthetic Argon2 input; never use these credentials for deployment."""

import hashlib
import json
from importlib.metadata import version
from pathlib import Path

from argon2 import PasswordHasher

hasher = PasswordHasher()
encoded = hasher.hash("synthetic-fixture-password", salt=b"synthetic-salt01")
assert hasher.verify(encoded, "synthetic-fixture-password")
parameters = dict(time_cost=hasher.time_cost, memory_cost=hasher.memory_cost, parallelism=hasher.parallelism, hash_len=hasher.hash_len)
record = dict(fixture="fixed-synthetic-argon2-auth-v1", argon2_version=version("argon2-cffi"), parameters=parameters, password_hash=encoded, password_hash_sha256=hashlib.sha256(encoded.encode()).hexdigest())
Path("/fixture-output/auth-fixture.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({key:value for key,value in record.items() if key != "password_hash"}))
