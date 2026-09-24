import csv
import io
import json
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class IngestedRecord:
    source: str
    data: Any
    metadata: dict[str, Any] = field(default_factory=dict)


class FileIngestor:
    def __init__(self, encoding: str = "utf-8") -> None:
        self.encoding = encoding

    def ingest(self, path: str) -> list[IngestedRecord]:
        text = self._read(path)
        if path.endswith(".json"):
            return self._from_json(path, text)
        if path.endswith(".jsonl"):
            return self._from_jsonl(path, text)
        if path.endswith(".csv"):
            return self._from_csv(path, text)
        return [IngestedRecord(source=path, data=text)]

    def _read(self, path: str) -> str:
        with open(path, "r", encoding=self.encoding) as f:
            return f.read()

    def _from_json(self, source: str, text: str) -> list[IngestedRecord]:
        data = json.loads(text)
        if isinstance(data, list):
            return [IngestedRecord(source=source, data=item) for item in data]
        return [IngestedRecord(source=source, data=data)]

    def _from_jsonl(self, source: str, text: str) -> list[IngestedRecord]:
        records = []
        for line_no, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            records.append(IngestedRecord(source=source, data=record, metadata={"line": line_no}))
        return records

    def _from_csv(self, source: str, text: str) -> list[IngestedRecord]:
        reader = csv.DictReader(io.StringIO(text))
        records = []
        for row in reader:
            records.append(IngestedRecord(source=source, data=dict(row)))
        return records


class StringIngestor:
    def ingest(self, source: str, text: str) -> IngestedRecord:
        return IngestedRecord(source=source, data=text)


class URLIngestor:
    def __init__(self, encoding: str = "utf-8") -> None:
        self.encoding = encoding

    def ingest(self, url: str) -> IngestedRecord:
        import urllib.request

        with urllib.request.urlopen(url, timeout=10) as resp:
            charset = resp.headers.get_content_charset() or self.encoding
            text = resp.read().decode(charset)
        return IngestedRecord(source=url, data=text)
