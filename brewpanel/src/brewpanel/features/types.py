from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..core.app import Application


class Feature(Protocol):
    """What a feature plugin's class must provide.

    `__init__(self, app)` should be cheap (store `app`, do no I/O). All actual
    wiring -- event subscriptions, background tasks -- happens in `register()`,
    which `Application.bootstrap()` calls once for every discovered feature.
    """

    def __init__(self, app: "Application") -> None: ...

    def register(self) -> None: ...


@dataclass(frozen=True, slots=True)
class FeatureInfo:
    feature_id: str
    display_name: str
    description: str


@dataclass(frozen=True, slots=True)
class FeaturePlugin:
    info: FeatureInfo
    feature_cls: type[Feature]
