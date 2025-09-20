# Data Retention Policy

## Overview
This document outlines the data retention policies for the Open Banking MCP server, ensuring compliance with GDPR requirements and best practices for data minimization.

## Retention Principles

### Core Principles
- **Data Minimization**: Only retain data for the minimum period necessary
- **Purpose Limitation**: Data is retained only for the stated purposes
- **User Control**: Users can request deletion of their data at any time
- **Automatic Expiration**: Implemented automatic cleanup of expired data

## Data Categories and Retention Periods

### 1. Access Tokens
- **Retention Period**: Session-only (no persistence)
- **Storage**: In-memory only
- **Deletion**: Automatic upon server restart or session end
- **Purpose**: Enable API access during active session

### 2. Consent Records
- **Retention Period**: 90 days maximum
- **Storage**: In-memory with expiration timestamps
- **Deletion**: Automatic cleanup after expiration
- **Purpose**: Audit trail and consent management
- **Data Included**: Consent ID, purpose, scopes, timestamps

### 3. Application Logs
- **Retention Period**: 90 days
- **Storage**: Local log files with rotation
- **Deletion**: Automatic log rotation and cleanup
- **Purpose**: Debugging, security monitoring, audit trail
- **Data Included**: Request/response logs (PII redacted)

### 4. CSV Export Files
- **Retention Period**: User-controlled (no automatic deletion)
- **Storage**: Local filesystem (user's choice of location)
- **Deletion**: Manual deletion by user
- **Purpose**: User's own record-keeping and analysis
- **Data Included**: Transaction data formatted for HMRC reporting

### 5. Raw API Responses
- **Retention Period**: Not retained
- **Storage**: Not stored
- **Deletion**: N/A (never stored)
- **Purpose**: N/A
- **Rationale**: Raw data is processed and redacted immediately

## Deletion Process

### Automatic Deletion
1. **Consent Records**: Automatically deleted after 90 days
2. **Access Tokens**: Deleted upon session termination
3. **Log Files**: Rotated and deleted after 90 days
4. **Temporary Files**: Cleaned up after processing

### Manual Deletion (User-Initiated)
1. **CSV Files**: Users delete their own export files
2. **Consent Withdrawal**: Users can revoke consent through TrueLayer
3. **Data Export Requests**: Users can request data deletion

### Deletion Methods
- **Secure Deletion**: Files are securely deleted (not just marked as deleted)
- **Verification**: Deletion is logged for audit purposes
- **Confirmation**: Users receive confirmation of deletion when applicable

## Implementation Details

### Consent Ledger Cleanup
```python
# Automatic cleanup of expired consent records
def cleanup_expired_consents():
    current_time = datetime.now()
    expired_consents = [
        consent for consent in consent_ledger.consents
        if consent['expires_at'] < current_time
    ]
    for consent in expired_consents:
        consent_ledger.remove_consent(consent['id'])
```

### Log Rotation
- **Daily Rotation**: Log files are rotated daily
- **Compression**: Old logs are compressed to save space
- **Deletion**: Logs older than 90 days are automatically deleted
- **PII Redaction**: All logs have PII redacted before storage

### Token Management
- **Session-Based**: Tokens are stored in memory only
- **Automatic Expiry**: Tokens expire according to provider settings
- **No Persistence**: Tokens are never written to disk
- **Secure Handling**: Tokens are redacted in all logs

## User Rights

### Right to Erasure (Article 17 GDPR)
- **Immediate Effect**: Users can revoke consent immediately
- **Data Deletion**: All associated data is deleted upon consent withdrawal
- **Confirmation**: Users receive confirmation of deletion
- **No Exceptions**: No legal basis for retaining data after withdrawal

### Right to Data Portability (Article 20 GDPR)
- **Export Functionality**: CSV export provides data portability
- **Standard Format**: Data exported in standard CSV format
- **Complete Data**: All available data is included in exports
- **User Control**: Users control when and what data to export

### Right to Access (Article 15 GDPR)
- **Consent Records**: Users can view their consent history
- **Data Categories**: Clear documentation of what data is processed
- **Processing Purposes**: Transparent documentation of data usage
- **Retention Periods**: Clear information about data retention

## Compliance Monitoring

### Regular Reviews
- **Monthly**: Review of retention policy effectiveness
- **Quarterly**: Audit of data deletion processes
- **Annually**: Full review of retention periods and policies

### Audit Trail
- **Deletion Logs**: All deletions are logged with timestamps
- **Consent Changes**: All consent modifications are tracked
- **Access Logs**: All data access is logged (with PII redaction)
- **Retention Compliance**: Regular checks for compliance with retention periods

## Exceptions and Special Cases

### Legal Requirements
- **Regulatory Holds**: Data may be retained longer if required by law
- **Legal Proceedings**: Data may be retained for legal proceedings
- **Audit Requirements**: Data may be retained for audit purposes

### Technical Limitations
- **Backup Systems**: Data in backups follows same retention rules
- **Cache Systems**: Cached data follows same retention rules
- **Error Logs**: Error logs may be retained longer for debugging

## Contact Information

For questions about data retention or to request data deletion:
- **Email**: [Contact information to be added]
- **Repository**: [GitHub repository issues]
- **Documentation**: See main project README

---

**Document Version**: 1.0
**Last Updated**: September 2024
**Next Review**: December 2024

