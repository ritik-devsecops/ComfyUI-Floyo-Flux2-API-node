import time
from typing import Any, Dict, List, Optional

import requests

from .flux2_config import Flux2Config


class Flux2APIError(Exception):
    """Raised when the FLUX.2 API returns an error or an unexpected response."""


class Flux2API:
    """Minimal client for the Black Forest Labs FLUX.2 [pro] endpoint."""

    BASE_URL = "https://api.bfl.ai/v1/flux-2-pro"

    def __init__(self, timeout: int = 600, poll_interval: float = 1.0):
        self.timeout = timeout
        self.poll_interval = poll_interval

        api_key = Flux2Config().get_key()
        if not api_key:
            raise Flux2APIError(
                "BFL_API_KEY is not set. Define it in config.ini or export BFL_API_KEY before running ComfyUI."
            )

        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "x-key": api_key,
        }

    @staticmethod
    def _strip_empty(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Remove keys with None or empty-string values so we only send what the API needs."""
        cleaned: Dict[str, Any] = {}
        for key, value in payload.items():
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            cleaned[key] = value
        return cleaned

    def submit_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a generation/editing request and return the raw API response."""
        body = self._strip_empty(payload)
        response = requests.post(self.BASE_URL, headers=self.headers, json=body, timeout=30)
        response.raise_for_status()

        data = response.json()
        if "polling_url" not in data:
            raise Flux2APIError("FLUX.2 API response did not include a polling_url.")
        if "id" not in data:
            raise Flux2APIError("FLUX.2 API response did not include a request id.")
        return data

    def poll_result(self, polling_url: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Poll the provided polling_url until the job is ready or fails."""
        start_time = time.time()
        last_status: Optional[str] = None

        while (time.time() - start_time) < self.timeout:
            response = requests.get(
                polling_url,
                headers=self.headers,
                params={"id": request_id} if request_id else None,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()

            status = payload.get("status")
            if status != last_status:
                print(f"[Flux2] Status: {status}")
                last_status = status

            if status == "Ready":
                return payload
            if status in {"Error", "Failed", "Content Moderated", "Request Moderated"}:
                raise Flux2APIError(f"FLUX.2 request failed with status '{status}': {payload}")

            time.sleep(self.poll_interval)

        raise Flux2APIError(f"Timed out after {self.timeout}s while waiting for the FLUX.2 result.")

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a request and wait for completion, returning convenience fields and raw payloads."""
        initial = self.submit_request(payload)
        polling_url = initial["polling_url"]
        request_id = initial.get("id")
        print(f"[Flux2] Submitted request: {request_id}")

        final = self.poll_result(polling_url, request_id=request_id)
        sample_url = final.get("result", {}).get("sample")
        cost = initial.get("cost")
        return {
            "sample": sample_url,
            "cost": cost,
            "request": initial,
            "result": final,
        }


def merge_reference_images(main_image: str, additional_images: List[str]) -> Dict[str, str]:
    """
    Build the payload keys for multi-reference inputs.

    FLUX.2 [pro] accepts input_image + up to 7 extras: input_image_2 ... input_image_8.
    """
    payload: Dict[str, str] = {}
    if main_image:
        payload["input_image"] = main_image

    for idx, image in enumerate(additional_images, start=2):
        if idx > 8:
            break
        if image and image.strip():
            payload[f"input_image_{idx}"] = image.strip()

    return payload
