class ProductionReadiness:
    def __init__(self):
        self.checks = {}

    def add_check(self, name, checker):
        self.checks[name] = checker

    def evaluate(self):
        results = {}
        for name, checker in self.checks.items():
            results[name] = checker.run()
        return results

    def score(self):
        total = 0
        passed = 0
        for checker in self.checks.values():
            total += 1
            if checker.run().get("passed"):
                passed += 1
        return {"total": total, "passed": passed, "score": passed / total if total else 0}
