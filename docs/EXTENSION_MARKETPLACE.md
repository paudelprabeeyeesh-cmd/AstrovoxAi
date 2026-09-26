# Extension Marketplace

The Extension Marketplace is the curated catalog of IDE integrations, browser extensions, and CLI plugins.

## Browsing

- Open `frontend/developer.html` → **Marketplace** tab
- Or use the CLI:

```bash
astrovox marketplace search vscode
astrovox marketplace search "productivity"
```

## Categories

| Category | Examples |
|----------|----------|
| IDE | VS Code, JetBrains, Neovim |
| Browser | Chrome, Firefox, Safari |
| CLI | Astrovox CLI plugins |
| Templates | Agent starters, integration kits |

## Publishing Extensions

```bash
# Package
astrovox package ./my-extension

# Submit to marketplace
astrovox marketplace submit ./my-extension.tar.gz --category ide
```

## Verification

All marketplace items are verified before listing:

1. Manifest signature check
2. Permission scope audit
3. Static analysis for dangerous patterns
4. Sandbox execution test suite
5. Maintainer identity verification

## Ratings & Reviews

- Users can rate and review extensions
- Ratings are weighted by usage and recency
- Maintainers can respond to reviews

## Versioning

- Extensions track the AstrovoxAI platform version they target
- Compatibility warnings are shown when installing on an older platform
- Auto-update is opt-in per extension

## Revenue (Future)

- Maintainers may set commercial pricing
- AstrovoxAI takes a 15% platform fee
- Payouts are monthly via Stripe Connect
