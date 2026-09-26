from pathlib import Path
from typing import Dict

from sdk.docs_generator import SDKDocsGenerator
from sdk.generator import SDKGenerator
from sdk.openapi.spec import OpenAPISpec


def generate_sdk(spec: OpenAPISpec, output_dir: Path) -> Dict[str, Path]:
    generator = SDKGenerator(spec, output_dir)
    return generator.generate()


def generate_sdk_docs(sdk_root: Path, output_dir: Path) -> Dict[str, Path]:
    docs = SDKDocsGenerator(sdk_root, output_dir)
    return docs.generate()
