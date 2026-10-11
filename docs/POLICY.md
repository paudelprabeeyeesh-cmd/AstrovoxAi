# Usage and Content Policy

This is the human-readable policy that the safety test suites enforce.
Where the policy says a thing is refused, there is a test that encodes it;
where a thing is allowed, there is a benign test that guards against
over-blocking.

## 1. Scope

AstrovoxAI is a chat and retrieval product built on third-party models. It
routes requests to model vendors; it does not run a proprietary model. Users
are talking to an AI system, and the interface says so.

## 2. Prohibited (refuse)

Refusal is a short explanation of the boundary plus a safe alternative, not
a lecture.

- Content that sexualizes minors.
- Instructions for weapons, explosives, or biological agents intended to
  cause harm.
- Fraud, theft, or intrusion instructions targeting identifiable third
  parties.
- Hate content directed at protected characteristics.
- Instructions to self-harm or suicide.
- Non-consensual intimate imagery.
- Malware or intrusion tooling intended for use against targets the user
  is not authorized to test.

## 3. Allowed

- Dual-use security research where the user states an authorized scope.
- Creative fiction containing violence, including villain perspectives, with
  narrative framing.
- Critique of institutions and public figures.
- Medical, legal, and financial information with a "consult a professional"
  caveat.
- Refusal to answer with an explanation of which category applies.

## 4. Escalation

Requests that fall between 2 and 3 go to a human review queue rather than an
automatic refusal. The review queue is part of D15-10 (human evaluation
workflow) and is not yet implemented; until it is, ambiguous requests are
refused rather than allowed, and the refusal message names the category.

## 5. Crisis handling

Self-harm and crisis requests are answered with verified, region-appropriate
resources and a warm hand-off. The response avoids methods and avoids
promising outcomes. Expert review of the resource list is a precondition for
public launch (D16-04) and is not yet complete.

## 6. Enforcement in code

| Rule | Where |
|---|---|
| Input moderation | `app/safety/` |
| Injection corpus | `tests/security/test_prompt_injection.py` |
| Cross-tenant isolation | `tests/security/test_tenant_isolation.py` |
| Error envelope (no provider text leaks) | `tests/integration/test_api_contract.py` |

## 7. Transparency

The product discloses that responses are AI-generated, names the model in
use where the provider exposes it, and documents known weaknesses in the
README rather than omitting them.

## 8. Legal review

This policy is a draft. Counsel must review categories, escalation, and the
crisis protocol before publication. Nothing here is legal advice.