import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://agentproof:agentproof@localhost:5432/agentproof"
    )
    agent_write_credential: str = os.environ.get("AGENT_WRITE_CREDENTIAL", "agent-write-demo-credential")
    verifier_read_credential: str = os.environ.get("VERIFIER_READ_CREDENTIAL", "verifier-read-demo-credential")
    simulator_base_url: str = os.environ.get("SIMULATOR_BASE_URL", "http://127.0.0.1:8000")
    anthropic_api_key: str | None = os.environ.get("ANTHROPIC_API_KEY")
    claude_model: str = os.environ.get("CLAUDE_MODEL", "claude-opus-5")

    # Stripe — two separate restricted keys, same credential-separation
    # discipline as the simulator's AGENT_WRITE_CREDENTIAL /
    # VERIFIER_READ_CREDENTIAL. STRIPE_WRITE_KEY should be a Restricted Key
    # scoped to Write-only on Refunds/Charges; STRIPE_READ_KEY a separate
    # Restricted Key scoped to Read-only on Charges. Never the same key.
    stripe_api_base: str = os.environ.get("STRIPE_API_BASE", "https://api.stripe.com")
    stripe_write_key: str | None = os.environ.get("STRIPE_WRITE_KEY")
    stripe_read_key: str | None = os.environ.get("STRIPE_READ_KEY")


settings = Settings()
