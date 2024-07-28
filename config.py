from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongodb_url: str
    database_name: str
    secret_key: str
    encrypt_key: str
    api_key1: str
    api_key2: str
    net_model1:str
    net_model2:str
    temperature:int
    algorithm: str
    access_token_expire_minutes: int
    uploadOf_path:str
    pdfEval_path:str
    production: bool

    class Config:
        env_file = ".env"

settings = Settings()