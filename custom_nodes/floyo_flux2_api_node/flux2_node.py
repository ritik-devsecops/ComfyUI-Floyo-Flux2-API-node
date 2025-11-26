import configparser
import os
import time
from pathlib import Path
from typing import Any, Dict

import requests

CONFIG_PATH = Path(__file__).parent / "config.ini"
DEFAULT_BASE_URL = "https://api.bfl.ai/v1"
DEFAULT_MODEL = "flux-2-pro"


class FloyoFlux2APINode:
    """
    ComfyUI custom node that calls Black Forest Labs FLUX.2 API endpoints via URLs.

    Inputs are URL/base64 strings to align with Floyo's storage model. The node polls
    the `polling_url` returned by the API until the result is ready or a timeout occurs.
    """

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("image_url",)
    FUNCTION = "generate"
    CATEGORY = "Floyo/API"

    @classmethod
    def INPUT_TYPES(cls):
        required = {
            "prompt": ("STRING", {"multiline": True, "default": "Describe the image you want"}),
            "input_image": ("STRING", {"default": "https://example.com/your-image.jpg"}),
        }

        optional_images = {
            f"input_image_{i}": ("STRING", {"default": ""}) for i in range(2, 10)
        }

        optional = {
            **optional_images,
            "model": ("STRING", {"default": DEFAULT_MODEL, "choices": ["flux-2-pro", "flux-2-flex"]}),
            "width": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 16}),
            "height": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 16}),
            "seed": ("INT", {"default": -1, "min": -1, "max": 2**31 - 1}),
            "safety_tolerance": ("INT", {"default": 2, "min": 0, "max": 6}),
            "output_format": ("STRING", {"default": "jpeg", "choices": ["jpeg", "png"]}),
            "guidance": ("FLOAT", {"default": 4.5, "min": 1.5, "max": 10.0, "step": 0.1}),
            "steps": ("INT", {"default": 50, "min": 1, "max": 50}),
            "poll_interval": ("FLOAT", {"default": 0.5, "min": 0.1, "max": 5.0, "step": 0.1}),
            "max_wait_seconds": ("INT", {"default": 120, "min": 5, "max": 600}),
        }

        return {"required": required, "optional": optional}

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def generate(
        self,
        prompt: str,
        input_image: str,
        model: str = DEFAULT_MODEL,
        width: int = 0,
        height: int = 0,
        seed: int = -1,
        safety_tolerance: int = 2,
        output_format: str = "jpeg",
        guidance: float = 4.5,
        steps: int = 50,
        poll_interval: float = 0.5,
        max_wait_seconds: int = 120,
        **kwargs: Any,
    ):
        api_key, base_url, model, poll_interval, max_wait_seconds = self._load_config(
            model, poll_interval, max_wait_seconds
        )

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "input_image": input_image,
            "safety_tolerance": safety_tolerance,
            "output_format": output_format,
        }

        for key, value in kwargs.items():
            if key.startswith("input_image_") and isinstance(value, str) and value.strip():
                payload[key] = value

        if width > 0:
            payload["width"] = width
        if height > 0:
            payload["height"] = height
        if seed >= 0:
            payload["seed"] = seed

        if model == "flux-2-flex":
            payload["guidance"] = guidance
            payload["steps"] = steps

        endpoint = f"{base_url.rstrip('/')}/flux-2-{model.split('-')[-1]}"

        response = requests.post(
            endpoint,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "x-key": api_key,
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        polling_url = data.get("polling_url")
        if not polling_url:
            raise RuntimeError("API response missing polling_url.")

        image_url = self._poll_for_result(
            polling_url=polling_url,
            api_key=api_key,
            poll_interval=poll_interval,
            max_wait_seconds=max_wait_seconds,
        )

        return (image_url,)

    def _load_config(self, model: str, poll_interval: float, max_wait_seconds: int):
        config = configparser.ConfigParser()
        if CONFIG_PATH.exists():
            config.read(CONFIG_PATH)

        api_key = os.getenv("BFL_API_KEY") or config.get("auth", "api_key", fallback=None)
        if not api_key or "YOUR_BFL_API_KEY" in api_key:
            raise RuntimeError("BFL API key not configured. Set BFL_API_KEY env or update config.ini.")

        base_url = config.get("api", "base_url", fallback=DEFAULT_BASE_URL)
        configured_model = config.get("api", "model", fallback=model)
        effective_model = configured_model if configured_model in {"flux-2-pro", "flux-2-flex"} else model

        configured_interval = config.getfloat("api", "poll_interval", fallback=poll_interval)
        configured_timeout = config.getint("api", "max_wait_seconds", fallback=max_wait_seconds)

        return api_key, base_url, effective_model, configured_interval, configured_timeout

    def _poll_for_result(
        self,
        polling_url: str,
        api_key: str,
        poll_interval: float,
        max_wait_seconds: int,
    ) -> str:
        start_time = time.time()
        while True:
            result = requests.get(
                polling_url,
                headers={"accept": "application/json", "x-key": api_key},
                timeout=30,
            )
            result.raise_for_status()
            payload = result.json()
            status = payload.get("status")

            if status == "Ready":
                result_obj = payload.get("result", {})
                image_url = result_obj.get("sample")
                if not image_url:
                    raise RuntimeError("Result missing sample URL.")
                return image_url

            if status in {"Error", "Failed", "Content Moderated", "Request Moderated"}:
                raise RuntimeError(f"Generation failed with status: {status} - {payload}")

            if time.time() - start_time > max_wait_seconds:
                raise TimeoutError("Polling timed out before result was ready.")

            time.sleep(poll_interval)


NODE_CLASS_MAPPINGS = {"FloyoFlux2APINode": FloyoFlux2APINode}
NODE_DISPLAY_NAME_MAPPINGS = {"FloyoFlux2APINode": "Floyo FLUX.2 API"}
