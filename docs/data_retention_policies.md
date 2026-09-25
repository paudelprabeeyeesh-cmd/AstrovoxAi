# Data Retention Policies

## User Data
- **Active accounts**: Retain indefinitely
- **Deleted accounts**: 30 days (GDPR right to erasure)
- **Anonymous usage data**: 90 days

## Conversation Data
- **Free tier**: 30 days
- **Pro tier**: 1 year
- **Enterprise**: 3 years (configurable)

## Audit Logs
- **Authentication events**: 2 years
- **Authorization events**: 2 years
- **Data access**: 1 year
- **System events**: 90 days

## Metrics
- **Prometheus metrics**: 30 days
- **Application logs**: 90 days
- **Error logs**: 1 year

## Backups
- **Daily backups**: 30 days retention
- **Weekly backups**: 1 year retention
- **Monthly backups**: 7 years retention

## Deletion Process
1. User requests deletion
2. Soft delete with 30-day grace period
3. Hard delete after grace period
4. Verify deletion across all systems
5. Generate deletion certificate

## Compliance
- GDPR Article 17: Right to erasure
- SOC 2: Data retention requirements
- Industry-specific: Healthcare (7 years), Finance (7 years)
