from dataclasses import dataclass
from typing import List, Callable, Any
import pandas as pd


@dataclass
class BatchJob:
    name: str
    source: str
    transformer: Callable[[pd.DataFrame], pd.DataFrame]
    sink: str


class BatchProcessor:
    def __init__(self, jobs: List[BatchJob]):
        self.jobs = jobs

    def run(self) -> None:
        for job in self.jobs:
            df = pd.read_parquet(job.source)
            transformed = job.transformer(df)
            transformed.to_parquet(job.sink, index=False)
