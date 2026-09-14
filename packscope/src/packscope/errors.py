# SPDX-License-Identifier: Apache-2.0
"""Domain-specific errors with actionable messages for integration users."""


class PackScopeError(Exception):
    """Base exception for recoverable PackScope failures."""


class ConfigurationError(PackScopeError):
    """Raised when a caller provides incompatible or incomplete configuration."""


class CalibrationError(PackScopeError):
    """Raised when gaze calibration data are insufficient or degenerate."""


class DataQualityError(PackScopeError):
    """Raised when a caller explicitly requires analysis despite failed quality checks."""


class DeviceProtocolError(PackScopeError):
    """Raised when a device payload cannot be decoded safely."""


class OptionalDependencyError(PackScopeError):
    """Raised when a requested hardware backend has not been installed."""

    def __init__(self, dependency: str, extra: str) -> None:
        super().__init__(
            f"Optional dependency '{dependency}' is required. Install it with: "
            f"python -m pip install 'packscope[{extra}]'"
        )
