"""Research source bibliography registry."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceRecord:
    url: str
    title: str | None = None
    via: str = "read_webpage"


@dataclass
class SourceRegistry:
    records: list[SourceRecord] = field(default_factory=list)

    def register(self, url: str, *, title: str | None = None, via: str = "read_webpage") -> bool:
        if any(r.url == url for r in self.records):
            return False
        self.records.append(SourceRecord(url=url, title=title, via=via))
        return True

    def format_bibliography_markdown(self) -> str:
        if not self.records:
            return ""
        lines = ["## References"]
        for i, rec in enumerate(self.records, start=1):
            label = rec.title or rec.url
            lines.append(f"{i}. [{label}]({rec.url})")
        return "\n".join(lines) + "\n"
