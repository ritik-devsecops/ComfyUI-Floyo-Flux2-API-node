# Floyo FLUX.2 API Custom Node

A Floyo-ready ComfyUI custom node for the Black Forest Labs FLUX.2 API. The node mirrors Floyo's URL-first I/O pattern, supports both **flux-2-pro** and **flux-2-flex** variants, and polls the API's `polling_url` until an image URL is returned.

## Features
- URL/Base64 inputs for the base image plus up to eight additional reference images.
- Model selector for `flux-2-pro` (fast, production) or `flux-2-flex` (adjustable steps & guidance).
- Optional sizing, seed, safety tolerance, and output format controls.
- Flex-only parameters: guidance and steps.
- Configurable polling interval and timeout aligned with BFL recommendations.

## Installation
1. Copy the `custom_nodes/floyo_flux2_api_node` folder into your ComfyUI `custom_nodes` directory (keep the `__init__.py` + `flux2_node.py` pairing intact so the node is auto-discovered).
2. Ensure `requests` is available in your Python environment.
3. Provide your Black Forest Labs API key via either:
   - Environment: `export BFL_API_KEY=your_key`
   - Config file: update `custom_nodes/floyo_flux2_api_node/config.ini` (`[auth] api_key`)

## Configuration
`config.ini` lets you set defaults without changing the node code:

```ini
[auth]
api_key = YOUR_BFL_API_KEY

[api]
base_url = https://api.bfl.ai/v1
model = flux-2-pro
poll_interval = 0.5
max_wait_seconds = 120
```

> The node falls back to `BFL_API_KEY` if it is set. The placeholder value must be replaced.

## Node Inputs
- **prompt** (string, required): Edit or generation prompt.
- **input_image** (string, required): URL or base64 image to edit; also works for text-to-image prompts.
- **input_image_2 ... input_image_9** (string, optional): Additional reference images.
- **model** (`flux-2-pro` \| `flux-2-flex`): Selects the target endpoint.
- **width / height** (int, optional): Multiples of 16; defaults to matching input.
- **seed** (int, optional): `-1` for random.
- **safety_tolerance** (0-6): Moderation strictness.
- **output_format** (`jpeg` \| `png`).
- **guidance**, **steps**: Only applied when model = `flux-2-flex`.
- **poll_interval**, **max_wait_seconds**: Override the default polling cadence.

## Output
- **image_url**: The signed URL returned by the FLUX.2 API (`result.sample`). Download and re-serve the image within 10 minutes per BFL delivery rules.

## Workflow Tips
- Keep inputs as URLs to align with Floyo's storage and queueing behavior.
- Multi-reference editing: supply additional `input_image_*` fields to mix styles and content.
- For flex runs, tweak `guidance` (1.5-10) and `steps` (<=50) for quality/performance tradeoffs.
- Respect BFL rate limits and poll using the provided `polling_url` rather than a hardcoded endpoint.

## Example (Python)
```python
import os
import requests

api_key = os.environ["BFL_API_KEY"]
resp = requests.post(
    "https://api.bfl.ai/v1/flux-2-pro",
    headers={"x-key": api_key, "accept": "application/json"},
    json={
        "prompt": "Cinematic city sunset, 85mm lens",
        "input_image": "https://example.com/source.jpg",
        "output_format": "jpeg",
    },
).json()

polling_url = resp["polling_url"]
result = requests.get(polling_url, headers={"x-key": api_key}).json()
print(result)
```

## Notes
- Delivery URLs expire after ~10 minutes and are not CORS-enabled; download and serve from your own storage.
- For regional routing, adjust `base_url` to `https://api.eu.bfl.ai/v1` or `https://api.us.bfl.ai/v1` in `config.ini`.
