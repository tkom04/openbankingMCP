"""
PKCE (Proof Key for Code Exchange) implementation for OAuth 2.0.

Provides secure OAuth 2.0 authorization code flow with PKCE support.
"""

import os
import secrets
import hashlib
import base64
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta


def generate_code_verifier() -> str:
    """Generate a cryptographically random code verifier for PKCE."""
    # RFC 7636: code_verifier = high-entropy cryptographic random STRING
    # using unreserved characters [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii').rstrip('=')


def generate_code_challenge(verifier: str) -> str:
    """Generate code challenge from verifier using SHA256 and base64url encoding."""
    # RFC 7636: code_challenge = base64url(sha256(code_verifier))
    digest = hashlib.sha256(verifier.encode('ascii')).digest()
    return base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')


def generate_random_state() -> str:
    """Generate a cryptographically random state parameter."""
    return secrets.token_urlsafe(32)


class ConsentLedger:
    """In-memory consent ledger for tracking user consents."""

    def __init__(self, ttl_days: int = 90):
        self.consents: Dict[str, Dict] = {}
        self.ttl_days = ttl_days

    def add_consent(self, consent_id: str, purpose: str, scopes: list, provider: str) -> str:
        """Add a new consent to the ledger."""
        now = datetime.utcnow()
        expires_at = now + timedelta(days=self.ttl_days)

        consent = {
            "id": consent_id,
            "purpose": purpose,
            "scopes": scopes,
            "provider": provider,
            "granted_at": now.isoformat(),
            "expires_at": expires_at.isoformat()
        }

        self.consents[consent_id] = consent
        return consent_id

    def get_consent(self, consent_id: str) -> Optional[Dict]:
        """Get a consent by ID if it exists and hasn't expired."""
        consent = self.consents.get(consent_id)
        if not consent:
            return None

        # Check if expired
        expires_at = datetime.fromisoformat(consent["expires_at"])
        if datetime.utcnow() > expires_at:
            del self.consents[consent_id]
            return None

        return consent

    def list_consents(self) -> list:
        """List all active consents."""
        active_consents = []
        now = datetime.utcnow()

        for consent_id, consent in list(self.consents.items()):
            expires_at = datetime.fromisoformat(consent["expires_at"])
            if now <= expires_at:
                active_consents.append(consent.copy())
            else:
                # Clean up expired consents
                del self.consents[consent_id]

        return active_consents

    def revoke_consent(self, consent_id: str) -> bool:
        """Revoke a consent by ID."""
        if consent_id in self.consents:
            del self.consents[consent_id]
            return True
        return False


class PKCEManager:
    """Manages PKCE flow state and verifiers."""

    def __init__(self):
        self.pending_flows: Dict[str, Dict] = {}

    def create_flow(self, state: str, code_verifier: str) -> Tuple[str, str, str]:
        """Create a new PKCE flow with state and verifier."""
        code_challenge = generate_code_challenge(code_verifier)

        # Store flow state with timestamp for cleanup
        self.pending_flows[state] = {
            "code_verifier": code_verifier,
            "code_challenge": code_challenge,
            "created_at": datetime.utcnow().isoformat()
        }

        return state, code_challenge, code_verifier

    def get_verifier(self, state: str) -> Optional[str]:
        """Get code verifier for a given state."""
        flow = self.pending_flows.get(state)
        if not flow:
            return None

        # Clean up the flow after retrieval
        del self.pending_flows[state]
        return flow["code_verifier"]

    def cleanup_expired_flows(self, max_age_minutes: int = 10):
        """Clean up expired PKCE flows."""
        now = datetime.utcnow()
        expired_states = []

        for state, flow in self.pending_flows.items():
            created_at = datetime.fromisoformat(flow["created_at"])
            if (now - created_at).total_seconds() > max_age_minutes * 60:
                expired_states.append(state)

        for state in expired_states:
            del self.pending_flows[state]


# Global instances
pkce_manager = PKCEManager()
consent_ledger = ConsentLedger(ttl_days=int(os.getenv("CONSENT_TTL_DAYS", "90")))
