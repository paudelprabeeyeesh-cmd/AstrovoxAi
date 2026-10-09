from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AttributeSpec:
    name: str
    values: List[str] = field(default_factory=list)


@dataclass
class ClassDescriptor:
    name: str
    attributes: Dict[str, List[str]] = field(default_factory=dict)


class AttributeClassifier:
    def __init__(self):
        self._classes: Dict[str, ClassDescriptor] = {}
        self._attribute_index: Dict[str, List[str]] = {}

    def register_class(self, descriptor: ClassDescriptor) -> None:
        self._classes[descriptor.name] = descriptor
        for attr, values in descriptor.attributes.items():
            self._attribute_index.setdefault(attr, [])
            for v in values:
                if v not in self._attribute_index[attr]:
                    self._attribute_index[attr].append(v)

    def _attribute_overlap(self, item_attrs: Dict[str, List[str]], class_name: str) -> float:
        descriptor = self._classes.get(class_name)
        if descriptor is None:
            return 0.0
        if not item_attrs or not descriptor.attributes:
            return 0.0
        matched = 0
        total = 0
        for attr, values in item_attrs.items():
            class_values = descriptor.attributes.get(attr, [])
            if class_values:
                total += len(values)
                for v in values:
                    if v in class_values:
                        matched += 1
        return matched / total if total > 0 else 0.0

    def classify(self, item_attributes: Dict[str, List[str]]) -> Optional[str]:
        best_class = None
        best_score = -1.0
        for class_name in self._classes:
            score = self._attribute_overlap(item_attrs=item_attributes, class_name=class_name)
            if score > best_score:
                best_score = score
                best_class = class_name
        return best_class if best_score > 0 else None

    def classify_with_scores(self, item_attributes: Dict[str, List[str]]) -> List[Tuple[str, float]]:
        scores = []
        for class_name in self._classes:
            score = self._attribute_overlap(item_attrs=item_attributes, class_name=class_name)
            scores.append((class_name, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def get_descriptor(self, name: str) -> Optional[ClassDescriptor]:
        return self._classes.get(name)

    def list_classes(self) -> List[str]:
        return list(self._classes.keys())
