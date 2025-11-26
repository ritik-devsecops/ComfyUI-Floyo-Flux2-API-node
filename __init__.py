from .nodes.flux2_node import (  # noqa: F401
    Flux2ProImageEdit,
    Flux2ProTextToImage,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)
from .nodes.flux2_flex_node import (  # noqa: F401
    Flux2FlexTextToImage,
    Flux2FlexImageEdit,
    NODE_CLASS_MAPPINGS as FLEX_NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS as FLEX_NODE_DISPLAY_NAME_MAPPINGS,
)

NODE_CLASS_MAPPINGS.update(FLEX_NODE_CLASS_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(FLEX_NODE_DISPLAY_NAME_MAPPINGS)

__all__ = [
    "Flux2ProTextToImage",
    "Flux2ProImageEdit",
    "Flux2FlexTextToImage",
    "Flux2FlexImageEdit",
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
]
