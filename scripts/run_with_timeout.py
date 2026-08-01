#!/usr/bin/env python3
"""Run a command with a hard timeout and terminate its process group."""

import os
import signal
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: run_with_timeout.py SECONDS COMMAND [ARG ...]", file=sys.stderr)
        return 2

    try:
        timeout = float(sys.argv[1])
    except ValueError:
        print("timeout must be a number", file=sys.stderr)
        return 2

    if timeout <= 0:
        print("timeout must be greater than zero", file=sys.stderr)
        return 2

    process = subprocess.Popen(
        sys.argv[2:],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )

    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Terminate the whole command group so a stuck child cannot survive.
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        if stdout:
            sys.stdout.write(stdout)
        if stderr:
            sys.stderr.write(stderr)
        return 124

    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
