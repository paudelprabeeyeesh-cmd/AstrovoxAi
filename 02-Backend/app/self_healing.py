class SelfHealingManager:
    def __init__(self):
        self.issues = []

    def detect_issue(self, metric, threshold):
        if metric < threshold:
            self.issues.append({"metric": metric, "threshold": threshold})
            return True
        return False

    def heal(self, component):
        for issue in self.issues:
            component.fix(issue)
        self.issues.clear()

    def status(self):
        return {"healing_issues": len(self.issues)}
