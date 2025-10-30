from asyncio import to_thread
from collections.abc import Callable
from subprocess import run
from typing import Any


def borrow_params[**P, T](_: Callable[P, Any]) -> Callable[[Callable[..., T]], Callable[P, T]]:
    return lambda f: f


@borrow_params(run)
def run_subprocess(*args, **kwargs):
    return to_thread(run, *args, **kwargs)
