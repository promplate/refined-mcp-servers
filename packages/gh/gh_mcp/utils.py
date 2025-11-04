from collections.abc import Callable
from itertools import count
from subprocess import PIPE, CompletedProcess
from typing import Any

from anyio import run_process
from fastmcp.exceptions import ToolError


def borrow_params[**P, T](_: Callable[P, Any]) -> Callable[[Callable[..., T]], Callable[P, T]]:
    return lambda f: f


@borrow_params(run_process)
async def run_subprocess(command: list[str], **kwargs):
    for retry in count():
        r = await run_process(command, check=False, stdout=PIPE, stderr=PIPE, **kwargs)
        ret = CompletedProcess(command, r.returncode, r.stdout.decode(), r.stderr.decode())
        if ret.returncode == 4:
            raise ToolError("[[ No GitHub credentials found. Please log in to gh CLI or provide --token parameter when starting this MCP server! ]]")
        if ret.returncode < 2:
            if ret.stderr and not ret.stdout:  # transient network issue
                if retry < 5:
                    continue
                else:
                    raise ToolError(ret.stderr.strip())
            return ret
        if retry < 3:
            msg = f"gh returned non-zero exit code {ret.returncode}"
            raise ToolError(f"{msg}:\n{details}" if (details := ret.stdout or ret.stderr) else msg)

    assert False, "unreachable code"
