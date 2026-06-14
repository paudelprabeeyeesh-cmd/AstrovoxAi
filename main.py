import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_PATH = ROOT / '02-Backend' / 'server' / 'app.py'

spec = importlib.util.spec_from_file_location('_appAstravox', APP_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
app = module.create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
