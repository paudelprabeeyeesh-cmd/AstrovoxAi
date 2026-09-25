from sdk.openapi.spec import OpenAPISpec
from sdk.generator import SDKGenerator


def generate_sdk(spec: OpenAPISpec, output_dir: Path) -> Dict[str, Path]:
    generator = SDKGenerator(spec, output_dir)
    return generator.generate()
