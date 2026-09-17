class SecureSandbox:
    def __init__(self, policy):
        self.policy = policy

    def execute(self, code, environment):
        if not self.policy.allows(code):
            raise PermissionError("Code violates sandbox policy")
        return environment.run(code)

    def validate(self, code):
        return self.policy.allows(code)
