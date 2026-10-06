# Astrovox 1.0 RC1 - Quick Start Guide

Get up and running with Astrovox in under 5 minutes.

## Prerequisites

- Python 3.10, 3.11, or 3.12
- pip package manager
- 4GB+ RAM recommended

## Installation

```bash
# Clone the repository
git clone https://github.com/astrovox-ai/astrovox.git
cd astrovox

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import astrovox; print('Astrovox installed successfully!')"
```

**Time: ~2 minutes**

## Quick Validation

```bash
# Run unit tests
python -m pytest tests/ -q

# Expected output: 664 passed, 17 skipped
```

**Time: ~1 minute**

## Your First Example

```bash
# Generate text with a tiny model
python examples/train_tiny.py

# Expected output: Model training completes in <30 seconds
```

**Time: ~1 minute**

## Next Steps

- Explore `examples/` for more use cases
- Read `docs/` for detailed documentation
- Check `API.md` for API reference

## Troubleshooting

**Import errors?** Ensure you're in the repository root directory.

**Memory errors?** Use a smaller model config or reduce batch size.

**Slow tests?** Run with `pytest tests/ -k "not gpu and not distributed"` to skip GPU/distributed tests.

## Support

- Issues: https://github.com/astrovox-ai/astrovox/issues
- Docs: https://astrovox.ai/docs
- Discord: https://discord.gg/astrovox

---

**Total time: Under 5 minutes**
