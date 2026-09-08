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


settings = Settings()
