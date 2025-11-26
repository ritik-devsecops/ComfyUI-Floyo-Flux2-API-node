from typing import List, Optional

from .flux2_utils import (
    Flux2API,
    download_image_to_tensor,
    image_tensor_to_base64,
    merge_reference_images,
)
from .flux2_utils import _blank_image_tensor as _blank_image
from .flux2_config import Flux2Config


def _validate_resolution(width: int, height: int) -> Optional[str]:
    """Validate resolution constraints for FLUX.2 flex."""
    for dim_name, dim in (("width", width), ("height", height)):
        if dim <= 0:
            continue  # 0 means "use default/match input" for edits; for T2I user must set
        if dim % 16 != 0:
            return f"{dim_name} must be a multiple of 16 (got {dim})."
        if dim < 64 or dim > 2048:
            return f"{dim_name} must be between 64 and 2048 pixels (got {dim})."
    return None


class Flux2FlexTextToImage:
    """
    FLUX.2 [flex] text-to-image node for Floyo.

    Adds guidance/steps controls; outputs IMAGE tensor.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "", "tooltip": "Describe what to generate."}),
                "width": ("INT", {"default": 1024, "min": 64, "max": 2048, "step": 16, "tooltip": "Output width (multiple of 16, 64-2048)."}),
                "height": ("INT", {"default": 1024, "min": 64, "max": 2048, "step": 16, "tooltip": "Output height (multiple of 16, 64-2048)."}),
                "guidance": ("FLOAT", {"default": 4.5, "min": 1.5, "max": 10.0, "step": 0.1, "tooltip": "Prompt adherence (1.5-10)."}),
                "steps": ("INT", {"default": 50, "min": 1, "max": 50, "step": 1, "tooltip": "Inference steps (1-50)."}),
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
    CATEGORY = "Floyo/Flux2 Flex"

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        guidance: float,
        steps: int,
        seed: int = -1,
        safety_tolerance: int = 2,
        output_format: str = "jpeg",
    ):
        try:
            resolution_error = _validate_resolution(width, height)
            if resolution_error:
                return (f"Error: {resolution_error}",)

            cfg = Flux2Config()
            client = Flux2API(base_url=cfg.get_flex_base_url())
            payload = {
                "prompt": prompt,
                "width": width if width > 0 else None,
                "height": height if height > 0 else None,
                "seed": None if seed is None or seed < 0 else seed,
                "safety_tolerance": safety_tolerance,
                "output_format": output_format,
                "guidance": guidance,
                "steps": steps,
            }

            run_result = client.run(payload)
            image_url = run_result.get("sample")
            if not image_url:
                print("Error: FLUX.2 flex response did not include an image URL.")
                return (_blank_image(),)

            image_tensor = download_image_to_tensor(image_url)
            return (image_tensor,)
        except Exception as exc:  # noqa: BLE001
            print(f"Error generating with FLUX.2 flex: {exc}")
            return (_blank_image(),)


class Flux2FlexImageEdit:
    """
    FLUX.2 [flex] image editing node for Floyo.

    Supports up to 10 references, guidance, steps; outputs IMAGE tensor.
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
                "input_image_9": ("IMAGE", {"tooltip": "Optional reference image #9."}),
                "input_image_10": ("IMAGE", {"tooltip": "Optional reference image #10."}),
                "width": ("INT", {"default": 1024, "min": 0, "max": 2048, "step": 16, "tooltip": "Override width (0 = keep). Multiple of 16."}),
                "height": ("INT", {"default": 1024, "min": 0, "max": 2048, "step": 16, "tooltip": "Override height (0 = keep). Multiple of 16."}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 0xFFFFFFFF, "tooltip": "-1 = random. Any other integer is reproducible."}),
                "safety_tolerance": ("INT", {"default": 2, "min": 0, "max": 6, "tooltip": "Moderation level 0 (strict) to 6 (permissive)."}),
                "output_format": (["jpeg", "png"], {"default": "jpeg", "tooltip": "Output format."}),
                "guidance": ("FLOAT", {"default": 4.5, "min": 1.5, "max": 10.0, "step": 0.1, "tooltip": "Prompt adherence (1.5-10)."}),
                "steps": ("INT", {"default": 50, "min": 1, "max": 50, "step": 1, "tooltip": "Inference steps (1-50)."}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "edit"
    CATEGORY = "Floyo/Flux2 Flex"

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
        input_image_9=None,
        input_image_10=None,
        width: int = 1024,
        height: int = 1024,
        seed: int = -1,
        safety_tolerance: int = 2,
        output_format: str = "jpeg",
        guidance: float = 4.5,
        steps: int = 50,
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

            refs = [
                input_image_2,
                input_image_3,
                input_image_4,
                input_image_5,
                input_image_6,
                input_image_7,
                input_image_8,
                input_image_9,
                input_image_10,
            ]
            ref_values: List[str] = []
            for tensor_val in refs:
                resolved = resolve_image(tensor_val)
                ref_values.append(resolved if resolved else "")

            reference_payload = merge_reference_images(base_image_value, ref_values)

            cfg = Flux2Config()
            client = Flux2API(base_url=cfg.get_flex_base_url())
            payload = {
                "prompt": prompt,
                **reference_payload,
                "width": width if width > 0 else None,
                "height": height if height > 0 else None,
                "seed": None if seed is None or seed < 0 else seed,
                "safety_tolerance": safety_tolerance,
                "output_format": output_format,
                "guidance": guidance,
                "steps": steps,
            }

            run_result = client.run(payload)
            image_url = run_result.get("sample")
            if not image_url:
                print("Error: FLUX.2 flex response did not include an image URL.")
                return (_blank_image(),)

            image_tensor = download_image_to_tensor(image_url)
            return (image_tensor,)
        except Exception as exc:  # noqa: BLE001
            print(f"Error editing with FLUX.2 flex: {exc}")
            return (_blank_image(),)


NODE_CLASS_MAPPINGS = {
    "Flux2FlexTextToImage": Flux2FlexTextToImage,
    "Flux2FlexImageEdit": Flux2FlexImageEdit,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Flux2FlexTextToImage": "FLUX.2-Flex Text-to-Image",
    "Flux2FlexImageEdit": "FLUX.2-Flex Image Edit",
}
