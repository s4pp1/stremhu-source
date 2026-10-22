from pydantic import BaseModel


class SelfSignedCertificate(BaseModel):
    fullchain: str
    privkey: str
    expires_at: int


class AcmeCertificateGenerate(BaseModel):
    ddns_provider_id: str
    ddns_provider_token: str
    host: str
    email: str
    account_key_pem: str | None = None


class AcmeCertificate(BaseModel):
    fullchain: str
    privkey: str
    expires_at: int
    account_key: str
