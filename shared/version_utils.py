"""
Version Utilities for Saydut Launcher
Semantic version parsing and comparison
"""
from typing import Tuple


def parse_version(version: str) -> Tuple[int, int, int]:
    """
    Parse semantic version string to tuple

    Handles formats: "1.2.3", "v1.2.3", "V1.2.3"
    Invalid parts default to 0.

    Args:
        version: Version string (e.g., "1.2.3", "v2.0.1")

    Returns:
        Tuple[int, int, int]: (major, minor, patch)

    Examples:
        >>> parse_version("1.2.3")
        (1, 2, 3)
        >>> parse_version("v2.0")
        (2, 0, 0)
        >>> parse_version("bad.version")
        (0, 0, 0)
    """
    v = (version or "").strip().lstrip("vV")

    parts = []
    for piece in v.split(".")[:3]:  # Only take first 3 parts
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)

    # Pad to 3 parts
    while len(parts) < 3:
        parts.append(0)

    return tuple(parts)  # type: ignore


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two semantic versions

    Args:
        v1: First version
        v2: Second version

    Returns:
        int: -1 if v1 < v2, 0 if equal, 1 if v1 > v2

    Examples:
        >>> compare_versions("1.2.3", "1.2.4")
        -1
        >>> compare_versions("2.0.0", "1.9.9")
        1
        >>> compare_versions("1.0.0", "v1.0.0")
        0
    """
    t1 = parse_version(v1)
    t2 = parse_version(v2)

    if t1 < t2:
        return -1
    elif t1 > t2:
        return 1
    return 0


def is_newer(current: str, latest: str) -> bool:
    """
    Check if 'latest' version is newer than 'current'

    Args:
        current: Current version
        latest: Latest version

    Returns:
        bool: True if latest > current

    Example:
        >>> is_newer("1.0.0", "1.1.0")
        True
        >>> is_newer("2.0.0", "1.9.0")
        False
    """
    return compare_versions(latest, current) > 0


def format_version(version: str) -> str:
    """
    Normalize version string format

    Args:
        version: Version string

    Returns:
        str: Normalized version (e.g., "1.2.3")

    Example:
        >>> format_version("v1.2")
        "1.2.0"
    """
    major, minor, patch = parse_version(version)
    return f"{major}.{minor}.{patch}"


def get_major_version(version: str) -> int:
    """Get major version number"""
    return parse_version(version)[0]


def get_minor_version(version: str) -> int:
    """Get minor version number"""
    return parse_version(version)[1]


def get_patch_version(version: str) -> int:
    """Get patch version number"""
    return parse_version(version)[2]
