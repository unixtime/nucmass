"""
Shared utilities for nucmass.

This module contains common functionality used across multiple modules,
reducing code duplication and ensuring consistent behavior.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import requests

from .config import Config, get_logger

logger = get_logger("utils")

# Rate limiting: track last request time per domain
_last_request_time: dict[str, float] = {}


def download_with_mirrors(
    mirrors: list[str],
    output_path: Path,
    validators: list[Callable[[str], tuple[bool, str]]] | None = None,
    headers: dict[str, str] | None = None,
    data_name: str = "data",
) -> Path:
    """
    Download a file from a list of mirror URLs with fallback.

    This function tries each mirror in order until one succeeds. It includes:
    - Rate limiting between requests to the same domain
    - Content validation to ensure the download is valid
    - Detailed logging for debugging download issues

    Args:
        mirrors: List of URLs to try in order.
        output_path: Where to save the downloaded file.
        validators: List of validation functions. Each takes content string
            and returns (is_valid, error_message). All must pass.
        headers: Optional HTTP headers to include in requests.
        data_name: Name of the data for logging (e.g., "AME2020", "NUBASE2020").

    Returns:
        Path to the downloaded file.

    Raises:
        RuntimeError: If download fails from all mirrors.

    Example:
        >>> validators = [
        ...     lambda c: (len(c) > 1000, "File too small"),
        ...     lambda c: ("<html" not in c[:500].lower(), "Received HTML"),
        ... ]
        >>> path = download_with_mirrors(
        ...     mirrors=["https://example.com/data.txt"],
        ...     output_path=Path("data.txt"),
        ...     validators=validators,
        ...     data_name="Example Data",
        ... )
    """
    # Return early if file already exists
    if output_path.exists():
        logger.info(f"{data_name} file already exists: {output_path}")
        return output_path

    # Default headers for browser-like requests
    if headers is None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }

    # Default validators if none provided
    if validators is None:
        validators = [
            lambda c: (len(c) >= 1000, f"File too small ({len(c)} bytes)"),
            lambda c: ("<html" not in c[:500].lower(), "Received HTML instead of data"),
        ]

    last_error: Exception | None = None

    for url in mirrors:
        try:
            # Rate limiting: respect server by waiting between requests
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if domain in _last_request_time:
                elapsed = time.time() - _last_request_time[domain]
                if elapsed < Config.REQUEST_DELAY:
                    time.sleep(Config.REQUEST_DELAY - elapsed)

            logger.info(f"Trying to download {data_name} from {url}...")
            response = requests.get(url, timeout=Config.DOWNLOAD_TIMEOUT, headers=headers)
            _last_request_time[domain] = time.time()
            response.raise_for_status()

            # Validate downloaded content
            content = response.text

            all_valid = True
            for validator in validators:
                is_valid, error_msg = validator(content)
                if not is_valid:
                    logger.warning(f"Validation failed: {error_msg}")
                    all_valid = False
                    break

            if not all_valid:
                continue

            # Save the file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content)
            logger.info(f"Saved {data_name} to {output_path} ({len(content):,} bytes)")
            return output_path

        except requests.RequestException as e:
            logger.warning(f"Failed to download from {url}: {e}")
            last_error = e
            continue

    raise RuntimeError(
        f"Could not download {data_name} from any mirror. Last error: {last_error}\n"
        "Please download manually from https://www.anl.gov/phy/atomic-mass-data-resources\n"
        f"and save to {output_path}"
    )


def validate_nuclide_params(z: int | None, n: int | None, a: int | None = None) -> None:
    """
    Validate nuclide parameters (Z, N, A).

    This is a unified validation function that checks all parameters
    against the configured valid ranges.

    Args:
        z: Proton number (can be None to skip validation).
        n: Neutron number (can be None to skip validation).
        a: Mass number (can be None to skip validation).

    Raises:
        InvalidNuclideError: If any parameter is invalid.
    """
    from .exceptions import InvalidNuclideError

    # Validate Z
    if z is not None:
        if not isinstance(z, int):
            raise InvalidNuclideError(f"Z must be an integer, got {type(z).__name__}")
        if z < Config.Z_MIN or z > Config.Z_MAX:
            raise InvalidNuclideError(
                f"Z={z} is out of valid range [{Config.Z_MIN}, {Config.Z_MAX}]",
                z=z
            )

    # Validate N
    if n is not None:
        if not isinstance(n, int):
            raise InvalidNuclideError(f"N must be an integer, got {type(n).__name__}")
        if n < Config.N_MIN or n > Config.N_MAX:
            raise InvalidNuclideError(
                f"N={n} is out of valid range [{Config.N_MIN}, {Config.N_MAX}]",
                n=n
            )

    # Validate A
    if a is not None:
        if not isinstance(a, int):
            raise InvalidNuclideError(f"A must be an integer, got {type(a).__name__}")
        max_a = Config.Z_MAX + Config.N_MAX
        if a < 1 or a > max_a:
            raise InvalidNuclideError(f"A={a} is out of valid range [1, {max_a}]")

    # Cross-check: if both Z and N provided, they should be consistent with A
    if z is not None and n is not None and a is not None:
        if a != z + n:
            raise InvalidNuclideError(
                f"Inconsistent parameters: A={a} but Z+N={z+n}",
                z=z, n=n
            )
