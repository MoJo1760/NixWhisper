"""Model utilities for NixWhisper."""

import torch
from typing import Tuple


def get_device_and_compute_type(device: str, compute_type: str) -> Tuple[str, str]:
    """Get device and compute type for model initialization.

    Args:
        device: Device to use (auto, cuda, cpu)
        compute_type: Compute type to use

    Returns:
        Tuple of (device, compute_type)
    """
    if device.lower() == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = compute_type if device == "cuda" else "int8"
    else:
        device = device.lower()

    return device, compute_type
