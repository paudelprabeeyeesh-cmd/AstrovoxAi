## Summary

_One or two sentences: what does this PR change, and why?_

## What it claims

_List each behaviour this PR adds or changes. Every line must correspond to a
test or a run you did — not to a file that now exists._

-

## Verification

_Replace each unchecked box with the command you actually ran and its result.
Delete the ones that don't apply to your change._

- [ ] `go build ./... && go vet ./... && go test -p 2 ./...`
- [ ] `python -m pytest tests --collect-only -q` (0 errors)
- [ ] `python tools/check_live_imports.py`
- [ ] `gofmt -l .` empty for touched files

```
<paste the relevant output here>
```

## Which module layer

_Live product code (`app`, `routes`, `api_gateway`, `sandboxing`, `database`,
`retrieval`, `memory_persistence`), or something outside that set? If outside,
which module from docs/MODULE_INVENTORY.md?_

## Security review

- [ ] No secrets, tokens, or credentials added
- [ ] No new `VITE_`-prefixed variable (those ship to the browser)
- [ ] No large binary files (>2 MB)
- [ ] If this touches auth, tenancy, or file upload: I have described the trust
      boundary and how I tested it

## Docs

- [ ] ADR updated if this contradicts a prior decision
- [ ] `docs/BASELINE.md` numbers still accurate if test behaviour changed

## Reviewer notes

_Anything you want challenged specifically? Anything you are unsure about?
This is the most useful section of the PR._