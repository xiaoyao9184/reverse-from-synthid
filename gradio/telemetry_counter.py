import asyncio
import inspect
import os
import threading
from functools import wraps
from contextlib import suppress

import gradio as gr
import requests

COUNTER_URL_ENV = "COUNTER_API_URL"
COUNTER_TOKEN_ENV = "COUNTER_API_TOKEN"
_PATCH = "_gradio_telemetry_counter_patch"

async def _update_counter(counter_url: str, bearer_token: str | None = None) -> None:
    headers = {}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    with suppress(Exception):
        await asyncio.to_thread(requests.get, counter_url, headers=headers, timeout=1)

def _schedule_counter_update(counter_url: str, bearer_token: str | None = None) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        threading.Thread(
            target=lambda: asyncio.run(_update_counter(counter_url, bearer_token)),
            daemon=True,
        ).start()
    else:
        loop.create_task(_update_counter(counter_url, bearer_token))


def _with_counter(fn, counter_url: str, bearer_token: str | None = None):
    if inspect.iscoroutinefunction(fn):
        @wraps(fn)
        async def async_wrapper(*args, **kwargs):
            _schedule_counter_update(counter_url, bearer_token)
            return await fn(*args, **kwargs)

        return async_wrapper

    @wraps(fn)
    def sync_wrapper(*args, **kwargs):
        _schedule_counter_update(counter_url, bearer_token)
        return fn(*args, **kwargs)

    return sync_wrapper

def patch_button_click(
    counter_url: str | None = None,
    bearer_token: str | None = None,
) -> None:
    if getattr(gr.Button.click, _PATCH, False):
        return

    counter_url = counter_url or os.getenv(COUNTER_URL_ENV)
    bearer_token = bearer_token or os.getenv(COUNTER_TOKEN_ENV)
    original_click = gr.Button.click

    @wraps(original_click)
    def patched_click(self, fn=None, *args, **kwargs):
        if fn is not None:
            fn = _with_counter(fn, counter_url, bearer_token)
        return original_click(self, fn=fn, *args, **kwargs)

    setattr(patched_click, _PATCH, True)
    gr.Button.click = patched_click
