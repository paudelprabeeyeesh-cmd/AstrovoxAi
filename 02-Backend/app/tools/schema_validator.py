"""Tool schema validation."""

from typing import Dict, Any, Optional
from pydantic import ValidationError, create_model


class SchemaValidator:
    _schemas: Dict[str, type] = {}

    @classmethod
    def register_schema(cls, name: str, schema: Dict[str, Any]) -> None:
        fields = {}
        for field_name, field_info in schema.get("properties", {}).items():
            field_type = str
            if field_info.get("type") == "integer":
                field_type = int
            elif field_info.get("type") == "number":
                field_type = float
            elif field_info.get("type") == "boolean":
                field_type = bool
            elif field_info.get("type") == "array":
                field_type = list
            elif field_info.get("type") == "object":
                field_type = dict
            default = field_info.get("default", ...)
            if default == ...:
                fields[field_name] = (field_type, ...)
            else:
                fields[field_name] = (field_type, default)
        required = schema.get("required", [])
        model = create_model(name, **{f: (fields[f][0], fields[f][1]) for f in fields})
        model.__required__ = required
        cls._schemas[name] = model

    @classmethod
    def validate(cls, name: str, data: Dict[str, Any]) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        model = cls._schemas.get(name)
        if not model:
            return False, None, f"Schema not found: {name}"
        try:
            validated = model(**data)
            return True, validated.dict(), None
        except ValidationError as e:
            return False, None, str(e)

    @classmethod
    def get_schema(cls, name: str) -> Optional[type]:
        return cls._schemas.get(name)
