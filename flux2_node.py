from typing import List

from .flux2_utils import Flux2API, merge_reference_images


def _validate_resolution(width: int, height: int) -> str | None:
    """Validate resolution constraints for FLUX.2."""
    for dim_name, dim in (("width", width), ("height", height)):
        if dim <= 0:
            continue  # 0 means "use default/match input"
        if dim % 16 != 0:
            return f"{dim_name} must be a multiple of 16 (got {dim})."
        if dim < 64 or dim > 2048:
            return f"{dim_name} must be between 64 and 2048 pixels (got {dim})."
    return None


class Flux2ProTextToImage:
    """
    FLUX.2 [pro] text-to-image node for Floyo.

    Accepts prompt + resolution and returns the signed image URL from the API.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "", "tooltip": "Describe what to generate. Supports long prompts (up to ~32k tokens per API docs)."}),
                "width": ("INT", {"default": 1024, "min": 64, "max": 2048, "step": 16, "tooltip": "Output width in pixels. Must be a multiple of 16. Range: 64-2048 (max ~4MP)."}),
                "height": ("INT", {"default": 1024, "min": 64, "max": 2048, "step": 16, "tooltip": "Output height in pixels. Must be a multiple of 16. Range: 64-2048 (max ~4MP)."}),
            },
            "optional": {
                "seed": ("INT", {"default": -1, "min": -1, "max": 0xFFFFFFFF, "tooltip": "-1 = random. Any other integer gives reproducible results."}),
                "safety_tolerance": ("INT", {"default": 2, "min": 0, "max": 6, "tooltip": "Moderation level. 0 = strict, 6 = most permissive (per BFL docs)."}),
                "output_format": (["jpeg", "png"], {"default": "jpeg", "tooltip": "Output format for the returned image URL."}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("image_url",)
    FUNCTION = "generate"
    CATEGORY = "Floyo/Flux2 Pro"

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int = -1,
        safety_tolerance: int = 2,
        output_format: str = "jpeg",
    ):
        try:
            resolution_error = _validate_resolution(width, height)
            if resolution_error:
                return (f"Error: {resolution_error}",)

            client = Flux2API()
            payload = {
                "prompt": prompt,
                "width": width if width > 0 else None,
                "height": height if height > 0 else None,
                "seed": None if seed is None or seed < 0 else seed,
                "safety_tolerance": safety_tolerance,
                "output_format": output_format,
            }

            run_result = client.run(payload)
            image_url = run_result.get("sample")
            if not image_url:
                return ("Error: FLUX.2 response did not include an image URL.",)

            return (image_url,)
        except Exception as exc:  # noqa: BLE001 - ComfyUI expects string errors
            return (f"Error generating with FLUX.2: {exc}",)


class Flux2ProImageEdit:
    """
    FLUX.2 [pro] image editing node for Floyo.

    Provide an input image URL plus optional reference images to guide edits.
    """

    @classmethod
    def INPUT_TYPES(cls):
        optional_refs = {
            f"input_image_{idx}": (
                "STRING",
                {"default": "", "tooltip": f"Optional reference image URL #{idx} (max 7 extras, total refs <= 8)."},
            )
            for idx in range(2, 9)
        }

        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "", "tooltip": "Describe the edit you want (what to change/keep)."}),
                "input_image": ("STRING", {"default": "", "tooltip": "Base image URL to edit. Required."}),
            },
            "optional": {
                **optional_refs,
                "width": ("INT", {"default": 0, "min": 0, "max": 2048, "step": 16, "tooltip": "Optional override. 0 = use input image width. Must be multiple of 16; range 64-2048 if set."}),
                "height": ("INT", {"default": 0, "min": 0, "max": 2048, "step": 16, "tooltip": "Optional override. 0 = use input image height. Must be multiple of 16; range 64-2048 if set."}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 0xFFFFFFFF, "tooltip": "-1 = random. Any other integer gives reproducible results."}),
                "safety_tolerance": ("INT", {"default": 2, "min": 0, "max": 6, "tooltip": "Moderation level. 0 = strict, 6 = most permissive (per BFL docs)."}),
                "output_format": (["jpeg", "png"], {"default": "jpeg", "tooltip": "Output format for the returned image URL."}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("image_url",)
    FUNCTION = "edit"
    CATEGORY = "Floyo/Flux2 Pro"

    def edit(
        self,
        prompt: str,
        input_image: str,
        input_image_2: str = "",
        input_image_3: str = "",
        input_image_4: str = "",
        input_image_5: str = "",
        input_image_6: str = "",
        input_image_7: str = "",
        input_image_8: str = "",
        width: int = 0,
        height: int = 0,
        seed: int = -1,
        safety_tolerance: int = 2,
        output_format: str = "jpeg",
    ):
        try:
            resolution_error = _validate_resolution(width, height)
            if resolution_error:
                return (f"Error: {resolution_error}",)

            additional_images: List[str] = [
                input_image_2,
                input_image_3,
                input_image_4,
                input_image_5,
                input_image_6,
                input_image_7,
                input_image_8,
            ]

            reference_payload = merge_reference_images(input_image, additional_images)

            if not reference_payload.get("input_image"):
                return ("Error: input_image URL is required for image editing.",)

            payload = {
                "prompt": prompt,
                **reference_payload,
                "width": width if width > 0 else None,
                "height": height if height > 0 else None,
                "seed": None if seed is None or seed < 0 else seed,
                "safety_tolerance": safety_tolerance,
                "output_format": output_format,
            }

            client = Flux2API()
            run_result = client.run(payload)
            image_url = run_result.get("sample")
            if not image_url:
                return ("Error: FLUX.2 response did not include an image URL.",)

            return (image_url,)
        except Exception as exc:  # noqa: BLE001 - ComfyUI expects string errors
            return (f"Error editing with FLUX.2: {exc}",)


NODE_CLASS_MAPPINGS = {
    "Flux2ProTextToImage": Flux2ProTextToImage,
    "Flux2ProImageEdit": Flux2ProImageEdit,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Flux2ProTextToImage": "FLUX.2 [pro] Text-to-Image",
    "Flux2ProImageEdit": "FLUX.2 [pro] Image Edit",
}
