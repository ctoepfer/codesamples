"""The single choke point every state-changing device call must pass through.

Every hardware reference in docs/hardware/ repeats some version of the same
warning: heater/pump/setpoint/mode/firmware operations need explicit
confirmation, audit logging, and (ideally) an operator physically present.
Rather than trusting every driver author to remember that, actuator methods
are wrapped with `@requires_confirmation` and route through a `SafetyGate`
that:

1. Refuses to act at all if nothing has registered a confirmation handler
   (fails closed, not open).
2. Calls the registered handler and waits for an explicit approve/deny.
3. Records every attempt -- approved or denied -- in an in-memory audit log.

A GUI wires a real confirmation dialog into `SafetyGate.set_confirmation_handler`.
Tests and scripts can wire an auto-approve or auto-deny stub. Either way, no
driver can silently skip the gate.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ParamSpec, TypeVar

logger = logging.getLogger("brewpanel.safety")

P = ParamSpec("P")
T = TypeVar("T")


class ConfirmationDenied(Exception):
    """Raised when a confirmation handler declines a state-changing call."""


class ConfirmationRequired(Exception):
    """Raised when a state-changing call is attempted with no confirmation handler registered."""


@dataclass(frozen=True, slots=True)
class ActuatorCall:
    device_id: str
    method_name: str
    args: tuple[object, ...]
    kwargs: dict[str, object]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


ConfirmationHandler = Callable[[ActuatorCall], Awaitable[bool]]


@dataclass(frozen=True, slots=True)
class AuditEntry:
    call: ActuatorCall
    approved: bool


class SafetyGate:
    """Owns the confirmation handler and the audit trail for one application instance."""

    def __init__(self) -> None:
        self._confirmation_handler: ConfirmationHandler | None = None
        self._audit_log: list[AuditEntry] = []

    def set_confirmation_handler(self, handler: ConfirmationHandler | None) -> None:
        self._confirmation_handler = handler

    async def confirm(self, call: ActuatorCall) -> bool:
        if self._confirmation_handler is None:
            raise ConfirmationRequired(
                f"No confirmation handler registered; refusing {call.method_name} on {call.device_id}"
            )
        approved = await self._confirmation_handler(call)
        self._audit_log.append(AuditEntry(call=call, approved=approved))
        logger.info(
            "actuator call device=%s method=%s approved=%s args=%r kwargs=%r",
            call.device_id,
            call.method_name,
            approved,
            call.args,
            call.kwargs,
        )
        return approved

    @property
    def audit_log(self) -> list[AuditEntry]:
        return list(self._audit_log)


_default_gate = SafetyGate()


def get_default_gate() -> SafetyGate:
    """The gate used by a driver instance that wasn't given its own `safety_gate`."""
    return _default_gate


def requires_confirmation(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """Decorator for any driver method that changes physical device state.

    Usage::

        class MyDevice(Device):
            @requires_confirmation
            async def set_heater(self, on: bool) -> None:
                ...  # actually talk to the hardware
    """

    @functools.wraps(func)
    async def wrapper(self: object, *args: P.args, **kwargs: P.kwargs) -> T:  # type: ignore[misc]
        gate: SafetyGate = getattr(self, "safety_gate", None) or get_default_gate()
        device_id = getattr(self, "device_id", "<unknown-device>")
        call = ActuatorCall(device_id=device_id, method_name=func.__name__, args=args, kwargs=kwargs)
        approved = await gate.confirm(call)
        if not approved:
            raise ConfirmationDenied(f"{call.method_name} on {call.device_id} was not confirmed")
        return await func(self, *args, **kwargs)  # type: ignore[arg-type]

    return wrapper
