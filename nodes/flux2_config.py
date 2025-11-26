import configparser
import os


class Flux2Config:
    """Singleton helper to load and expose the Black Forest Labs API key."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Config lives at repo root (parent of nodes/)
        config_path = os.path.join(os.path.dirname(current_dir), "config.ini")

        config = configparser.ConfigParser()
        config.read(config_path)

        key_from_env = os.environ.get("BFL_API_KEY")
        key_from_file = config.get("API", "BFL_API_KEY", fallback=None)
        base_from_env = os.environ.get("BFL_BASE_URL")
        base_from_file = config.get("API", "BFL_BASE_URL", fallback=None)

        if key_from_env:
            self._key = key_from_env
            print("BFL_API_KEY loaded from environment.")
        elif key_from_file:
            self._key = key_from_file
            os.environ.setdefault("BFL_API_KEY", self._key)
            print("BFL_API_KEY loaded from config.ini and set in environment.")
        else:
            self._key = None
            print("WARNING: No BFL_API_KEY found. Please set it in config.ini or as an environment variable.")

        default_base = "https://api.bfl.ai/v1/flux-2-pro"
        if base_from_env:
            self._base_url = base_from_env
            print(f"BFL_BASE_URL loaded from environment: {self._base_url}")
        elif base_from_file:
            self._base_url = base_from_file
            os.environ.setdefault("BFL_BASE_URL", self._base_url)
            print(f"BFL_BASE_URL loaded from config.ini: {self._base_url}")
        else:
            self._base_url = default_base
            print(f"BFL_BASE_URL not set; using default {default_base}")

        if self._key and self._key.strip() == "<your_bfl_api_key_here>":
            print("WARNING: BFL_API_KEY is still the placeholder value. Replace it with a real key from https://api.bfl.ai.")

    def get_key(self):
        """Return the configured API key or None when missing."""
        return self._key

    def get_base_url(self):
        """Return the configured base URL for FLUX.2 API."""
        return self._base_url
