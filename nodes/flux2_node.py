from typing import List, Optional

from .flux2_utils import (
    Flux2API,
    download_image_to_tensor,
    image_tensor_to_base64,
    merge_reference_images,
)
from .flux2_utils import _blank_image_tensor as _blank_image


def _validate_resolution(width: int, height: int) -> Optional[str]:
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
                "prompt": ("STRING", {"multiline": True, "default": "", "tooltip": "Describe what to generate."}),
                "width": ("INT", {"default": 1024, "min": 64, "max": 2048, "step": 16, "tooltip": "Output width (multiple of 16, 64-2048)."}),
                "height": ("INT", {"default": 1024, "min": 64, "max": 2048, "step": 16, "tooltip": "Output height (multiple of 16, 64-2048)."}),
            },
            "optional": {
                "seed": ("INT", {"default": -1, "min": -1, "max": 0xFFFFFFFF, "tooltip": "-1 = random. Any other integer is reproducible."}),
                "safety_tolerance": ("INT", {"default": 2, "min": 0, "max": 6, "tooltip": "Moderation level 0 (strict) to 6 (permissive)."}),
                "output_format": (["jpeg", "png"], {"default": "jpeg", "tooltip": "Output format."}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
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
                print("Error: FLUX.2 response did not include an image URL.")
                return (_blank_image(),)

            image_tensor = download_image_to_tensor(image_url)

            return (image_tensor,)
        except Exception as exc:  # noqa: BLE001 - ComfyUI expects string errors
            print(f"Error generating with FLUX.2: {exc}")
            return (_blank_image(),)


class Flux2ProImageEdit:
    """
    FLUX.2 [pro] image editing node for Floyo.

    Provide an input image URL plus optional reference images to guide edits.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "", "tooltip": "Describe the edit you want."}),
                "input_image": ("IMAGE", {"tooltip": "Base image."}),
            },
            "optional": {
                "input_image_2": ("IMAGE", {"tooltip": "Optional reference image #2."}),
                "input_image_3": ("IMAGE", {"tooltip": "Optional reference image #3."}),
                "input_image_4": ("IMAGE", {"tooltip": "Optional reference image #4."}),
                "input_image_5": ("IMAGE", {"tooltip": "Optional reference image #5."}),
                "input_image_6": ("IMAGE", {"tooltip": "Optional reference image #6."}),
                "input_image_7": ("IMAGE", {"tooltip": "Optional reference image #7."}),
                "input_image_8": ("IMAGE", {"tooltip": "Optional reference image #8."}),
                "width": ("INT", {"default": 1024, "min": 0, "max": 2048, "step": 16, "tooltip": "Override width (0 = keep). Multiple of 16."}),
                "height": ("INT", {"default": 1024, "min": 0, "max": 2048, "step": 16, "tooltip": "Override height (0 = keep). Multiple of 16."}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 0xFFFFFFFF, "tooltip": "-1 = random. Any other integer is reproducible."}),
                "safety_tolerance": ("INT", {"default": 2, "min": 0, "max": 6, "tooltip": "Moderation level 0 (strict) to 6 (permissive)."}),
                "output_format": (["jpeg", "png"], {"default": "jpeg", "tooltip": "Output format."}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "edit"
    CATEGORY = "Floyo/Flux2 Pro"

    def edit(
        self,
        prompt: str,
        input_image,
        input_image_2=None,
        input_image_3=None,
        input_image_4=None,
        input_image_5=None,
        input_image_6=None,
        input_image_7=None,
        input_image_8=None,
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

            def resolve_image(source_tensor) -> Optional[str]:
                if source_tensor is None:
                    return None
                try:
                    return image_tensor_to_base64(source_tensor, format="PNG")
                except Exception as exc:
                    print(f"Warning: failed to convert image tensor to base64: {exc}")
                    return None

            base_image_value = resolve_image(input_image)
            if not base_image_value:
                return ("Error: Provide a base image.",)

            reference_payload = {"input_image": base_image_value}

            refs = [
                input_image_2,
                input_image_3,
                input_image_4,
                input_image_5,
                input_image_6,
                input_image_7,
                input_image_8,
            ]

            for idx, tensor_val in enumerate(refs, start=2):
                resolved = resolve_image(tensor_val)
                if resolved:
                    reference_payload[f"input_image_{idx}"] = resolved

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
                print("Error: FLUX.2 response did not include an image URL.")
                return (_blank_image(),)

            image_tensor = download_image_to_tensor(image_url)

            return (image_tensor,)
        except Exception as exc:  # noqa: BLE001 - ComfyUI expects string errors
            print(f"Error editing with FLUX.2: {exc}")
            return (_blank_image(),)


NODE_CLASS_MAPPINGS = {
    "Flux2ProTextToImage": Flux2ProTextToImage,
    "Flux2ProImageEdit": Flux2ProImageEdit,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Flux2ProTextToImage": "FLUX.2 [pro] Text-to-Image",
    "Flux2ProImageEdit": "FLUX.2 [pro] Image Edit",
}
