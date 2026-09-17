class ModelRouterV2:
    def __init__(self):
        self.models = {}
        self.routing_rules = {}

    def register_model(self, model_id, config):
        self.models[model_id] = config

    def route(self, request):
        capabilities = request.get("capabilities", [])
        for rule_id, rule in self.routing_rules.items():
            if all(cap in rule.requires for cap in capabilities):
                return self.models[rule.model_id]
        raise ValueError("No suitable model found")

    def add_rule(self, rule_id, rule):
        self.routing_rules[rule_id] = rule
