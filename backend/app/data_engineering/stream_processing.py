from typing import Callable, Any
import json


class StreamProcessor:
    def __init__(self, source: Callable[[], Any], sink: Callable[[Any], None]):
        self.source = source
        self.sink = sink

    def process(self, transformer: Callable[[Any], Any]) -> None:
        for record in self.source():
            transformed = transformer(record)
            self.sink(transformed)
