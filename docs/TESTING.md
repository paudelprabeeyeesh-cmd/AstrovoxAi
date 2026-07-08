# TESTING

How to run tests locally and in CI for AstrovoxAI.

Frontend
- Install dev dependencies (locally):
  - npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @playwright/test
- Run unit tests: npm run test:unit (ensure a script is added to package.json or run npx vitest)
- Run e2e tests: npx playwright test (install browsers with npx playwright install)

Backend
- Create a virtualenv and install requirements:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r 02-Backend/requirements.txt
- Run backend tests:
  - cd 02-Backend
  - python -m pytest tests/ -v

CI Guidance
- The pipeline should run frontend unit tests, backend tests, and e2e smoke tests on PRs.
- To avoid modifying package.json, CI may install test-only dependencies at runtime with npm install --no-save or npx where appropriate.
