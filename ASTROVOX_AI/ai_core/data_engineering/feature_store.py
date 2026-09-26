from dataclasses import dataclass
from typing import Dict, Any, List
import pandas as pd
import numpy as np


@dataclass
class Feature:
    name: str
    dtype: str
    transformation: str


class FeatureStore:
    def __init__(self):
        self.features: Dict[str, Feature] = {}
        self._data: Dict[str, pd.DataFrame] = {}

    def register(self, feature: Feature) -> None:
        self.features[feature.name] = feature

    def compute(self, name: str, df: pd.DataFrame) -> pd.DataFrame:
        feature = self.features[name]
        if feature.transformation == "normalize":
            df[name] = (df[name] - df[name].mean()) / df[name].std()
        elif feature.transformation == "log":
            df[name] = df[name].apply(lambda x: np.log1p(x) if x > 0 else 0)
        self._data[name] = df[[name]]
        return df

    def get_feature(self, name: str) -> pd.DataFrame:
        return self._data.get(name)
