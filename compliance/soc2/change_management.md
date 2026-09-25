# Change Management Policy

## Purpose
Establishes a formal process for managing changes to production systems, infrastructure, and applications to meet SOC 2 CC3.2 and CC3.3 criteria.

## Change Types
- **Standard**: Pre-approved, low-risk changes (e.g., log rotation configuration).
- **Normal**: Changes requiring review and approval (e.g., database schema migrations).
- **Emergency**: Changes required to resolve a production incident; post-implementation review required.

## Change Control Process
1. **Request**: Developer submits a change request with description, risk assessment, and rollback plan.
2. **Review**: At least one peer and the Tech Lead review the request for correctness and security impact.
3. **Approval**: VP Engineering or designated approver signs off on production changes.
4. **Implementation**: Changes are deployed via CI/CD pipeline with automated testing.
5. **Verification**: Post-deployment smoke tests verify system health.
6. **Documentation**: All changes are recorded in the change management system with timestamps and approvers.

## Segregation of Duties
- Developers cannot approve their own changes for production.
- Emergency changes require post-hoc approval from VP Engineering within 48 hours.
- Database schema changes require DBA review for performance and data integrity.

## Change Freeze
- A change freeze is observed during critical business periods (e.g., fiscal year-end).
- Emergency changes during freeze require CTO approval.

## Metrics
- Change success rate, mean time to recover (MTTR), and change lead time are tracked in DORA metrics.
- Failed changes are reviewed in the weekly engineering sync.
