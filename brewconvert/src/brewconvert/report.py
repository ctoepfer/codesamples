from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class ConversionReport:
    source_format: str
    target_format: str
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def text(self) -> str:
        lines = [f"Converted {self.source_format} -> {self.target_format}"]
        for note in self.notes:
            lines.append(f"NOTE: {note}")
        for warning in self.warnings:
            lines.append(f"WARNING: {warning}")
        return "\n".join(lines)
