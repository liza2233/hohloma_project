from dataclasses import dataclass
import os
from decouple import config

@dataclass
class APIConfig:
    base_url: str = "https://app.platega.io/" 
    m_Id: str =  os.getenv(config("MERCHANT_ID"))
    x_s: str = os.getenv(config("X_SECRET"))
    timeout = 20
    headers = {"X-MerchantId": m_Id, "X-Secret": x_s, "Content-Type": "application/json"}
    