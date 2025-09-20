# Data Protection Impact Assessment (DPIA) - Lite

## Overview
This document provides a lightweight Data Protection Impact Assessment for the Open Banking MCP server, which provides access to bank account data through TrueLayer's Open Banking API.

## Data Processing Activities

### Personal Data Categories
- **Account Information**: Account names, types, balances
- **Transaction Data**: Transaction amounts, dates, descriptions, merchant information
- **Authentication Data**: OAuth tokens, consent identifiers

### Data Sources
- **Primary**: TrueLayer Open Banking API (sandbox/production)
- **Secondary**: User-provided OAuth authorization codes

### Data Subjects
- Bank account holders who authorize data access through TrueLayer

## Data Flow

### 1. Authorization Flow
```
User → TrueLayer OAuth → Authorization Code → MCP Server → Access Token
```

### 2. Data Retrieval Flow
```
MCP Server → TrueLayer API → Bank Data → User (via MCP tools)
```

### 3. Export Flow
```
Bank Data → CSV Processing → Local File → User Download
```

### 4. Consent Management
```
User Consent → PKCE State → Consent Ledger → Audit Trail
```

## Data Storage

### In-Memory Storage
- **Access Tokens**: Stored in memory during session only
- **Consent Records**: Stored in memory with expiration dates
- **No Persistent Storage**: Raw bank data is not persisted to disk

### Local Files (User-Initiated)
- **CSV Exports**: Generated on-demand, stored locally by user
- **Logs**: Application logs with PII redaction

## Lawful Basis for Processing

### Primary Basis: Consent (Article 6(1)(a) GDPR)
- **Explicit Consent**: Users explicitly authorize data access through TrueLayer OAuth
- **Granular Consent**: Users can specify scope of access (accounts, transactions, balance)
- **Withdrawal**: Users can revoke consent through TrueLayer's interface
- **Documentation**: Consent is logged with timestamp and purpose

### Secondary Considerations
- **Legitimate Interest**: For fraud prevention and security (Article 6(1)(f))
- **Contract Performance**: For providing requested banking services (Article 6(1)(b))

## Data Minimization

### Implemented Measures
- **Scope Limitation**: Only requested data scopes are accessed
- **Redaction**: Sensitive transaction details are redacted by default
- **No Raw Persistence**: Raw API responses are not stored
- **Selective Export**: Users choose specific date ranges and accounts

### Data Retention
- **Access Tokens**: Session-only (no persistence)
- **Consent Records**: 90 days maximum
- **Application Logs**: 90 days with PII redaction
- **CSV Exports**: User-controlled (local storage)

## Security Measures

### Technical Safeguards
- **PKCE OAuth**: Enhanced security for authorization flow
- **Token Redaction**: Access tokens are redacted in logs
- **HTTPS Only**: All API communications use TLS
- **Input Validation**: All user inputs are validated

### Organizational Safeguards
- **No Data Sharing**: Data is not shared with third parties
- **User Control**: Users control all data exports and retention
- **Transparency**: Clear documentation of data processing

## Risk Assessment

### Low Risk Factors
- **No Persistent Storage**: Raw data is not stored
- **User-Controlled**: Users initiate all data access
- **Limited Scope**: Only banking data relevant to user's accounts
- **Established API**: Uses regulated Open Banking APIs

### Mitigation Measures
- **Consent Management**: Comprehensive consent tracking
- **Data Redaction**: Sensitive data is redacted in logs
- **Regular Cleanup**: Automatic expiration of consent records
- **User Education**: Clear documentation of data usage

## Compliance Status

### GDPR Compliance
- ✅ **Lawful Basis**: Explicit consent documented
- ✅ **Data Minimization**: Only necessary data processed
- ✅ **Purpose Limitation**: Clear purpose for data processing
- ✅ **Transparency**: Users informed of data usage
- ✅ **User Rights**: Users control data access and export

### Open Banking Compliance
- ✅ **PSD2 Compliance**: Uses regulated Open Banking APIs
- ✅ **Consent Management**: Proper consent tracking
- ✅ **Security Standards**: PKCE and secure token handling

## Recommendations

### Ongoing Monitoring
- Regular review of consent records
- Monitor for unusual access patterns
- Keep security measures up to date

### User Education
- Provide clear consent explanations
- Document data usage purposes
- Offer easy consent withdrawal process

## Contact Information

For data protection queries, please refer to the main project documentation or contact the development team through the project repository.

---

**Document Version**: 1.0
**Last Updated**: September 2024
**Next Review**: December 2024

