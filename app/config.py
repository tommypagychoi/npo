from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Project Studio"
    API_TOKEN: str = "change-this-token"

    BASTION_HOST: str = "115.71.7.223"
    BASTION_PORT: int = 22
    BASTION_USER: str = "ubuntu"
    BASTION_KEY_PATH: str = "./ns.pem"
    STRICT_HOST_KEY: bool = False
    RUNNER_MODE: str = "ssh"

    KUBECONFIG_PATH: str = "/home/ubuntu/.kube/config"
    SSH_TIMEOUT: int = 12
    COMMAND_TIMEOUT: int = 45
    AUDIT_LOG_PATH: str = "./audit.log"
    MCP_SERVICE_PREFIX: str = "mcp"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1-mini"

    class Config:
        env_file = ".env"


settings = Settings()
