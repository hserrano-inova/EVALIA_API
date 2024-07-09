from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongodb_url: str
    database_name: str
    secret_key: str
    api_key: str
    net_model:str
    temperature:int
    algorithm: str
    access_token_expire_minutes: int
    uploadOf_path:str
    pdfEval_path:str
    production: bool

    class Config:
        env_file = ".env"

settings = Settings()