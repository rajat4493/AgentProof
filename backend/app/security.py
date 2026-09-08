"""Credential separation for the simulator (system of record).

Two distinct static credentials are enforced on every simulator request:

- AGENT_WRITE_CREDENTIAL — may call action (write) endpoints only.
- VERIFIER_READ_CREDENTIAL — may call read (verification) endpoints only.

Neither credential is accepted on the other's endpoints. AgentProof's
verifier must never hold or use the agent's write credential, and the agent
is never given the verifier's read credential.
"""

from fastapi import Header, HTTPException, status

from app.config import settings


def require_agent_write_credential(x_agentproof_credential: str = Header(...)) -> str:
    if x_agentproof_credential != settings.agent_write_credential:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or wrong-role credential for a write (action) endpoint.",
        )
    return "agent_write"


def require_verifier_read_credential(x_agentproof_credential: str = Header(...)) -> str:
    if x_agentproof_credential != settings.verifier_read_credential:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or wrong-role credential for a read (verification) endpoint.",
        )
    return "verifier_read"
