from fastapi import FastAPI, HTTPException, Query
import secrets
import asyncio
from fastapi.responses import PlainTextResponse
import httpx
from contextlib import asynccontextmanager
from bd.init_db import init_db
from bd.service import *
from utilities.update_config import update_config
from pydantic import BaseModel, Field
from typing import Optional, Literal
from decouple import config
from payments.transaction import Transaction

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    task = asyncio.create_task(update_config(config("CONFIG_PATH"), config("CONFIG_URL")))

    yield

    task.cancel()

app = FastAPI(lifespan=lifespan)



class HappResponseLimitation(BaseModel):
    """
    Модель ответа от Happ Proxy API (/api/add-install)

    {
        "rc": 1,
        "msg": "Ok",
        "install_code": "6P0hVao1fG5e"
    }
    """
    rc: int = Field(...)
    msg: str = Field(...)
    install_code: Optional[str] = Field(None)

    @property
    def is_success(self) -> bool:
        return self.rc == 1

    @property
    def error_message(self) -> Optional[str]:
        return self.msg if not self.is_success else None


async def limitation_link(provider_code: str, auth_key: str, install_limit: int) -> HappResponseLimitation:
    url = "https://api.happ-proxy.com/api/add-install"

    params = {
        "provider_code": provider_code,
        "auth_key": auth_key,
        "install_limit": install_limit
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            api_response = HappResponseLimitation.model_validate(response.json())

            if not api_response.is_success:
                raise HTTPException(
                    status_code=400,
                    detail=f"Happ Proxy error: {api_response.msg}"
                )

            return api_response
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Happ Proxy API timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot connect to Happ Proxy API")
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Happ Proxy HTTP error: {e.response.text}"
        )
    except Exception as e:
        # Логируем для отладки
        print(f"Unexpected error in limitation_link: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


async def create_enc_link(url: str):
    api_endpoint = "https://crypto.happ.su/api-v2.php"
    json_data = {"url": url}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            api_endpoint,
            json=json_data  # ← httpx автоматически:
                           #    1. Сериализует dict в JSON
                           #    2. Добавит заголовок Content-Type: application/json
        )
        result = response.json()
        result = result["encrypted_link"]
        return result


async def generate_link(user_id: int, token: str):
    #raw_limit_id = await limitation_link(config("PROVIDER_CODE"), config("AUTH_KEY"), config("INSTALL_LIMIT"))
    #limit_id = raw_limit_id.install_code
    url = f"http://{config("HOST")}/api/configs/{user_id}?token={token}"           #?installid={limit_id}"
    print(url)
    enc_url = await create_enc_link(url)
    return enc_url


def generate_token(user_id: int): # Генерация Токена
    token = secrets.token_urlsafe(43)
    return token


@app.get("/api/validate_user/{user_id}") # Проверить подписку
async def check_user_status(user_id: int):
    subscription = await is_validate_user(user_id)

    if subscription:
        token = subscription.token
        result_url = await generate_link(user_id, token)
        return {"message": "Подписка активна",
                "expires": subscription.expiration_date.date(),
                "url": result_url
                }
    else:
        return {"message": "Подписка не активна"}


@app.get("/api/subscribe/{user_id}") # Оплатить подписку
async def subscribe(user_id: int,  amount: float, currency: str, pay_meth: int = Query(..., gt=1, le =13)):
    new_trans = Transaction(user_id)
    result = await new_trans.get_link(pay_meth, amount, currency)
    trans_id = result["transaction_id"]
    return {"transaction_id": trans_id}



@app.get("/api/get_transacion_status/{user_id}/{transaction_id}")
async def check_transaction(user_id: int, transaction_id: str, days: int = Query(..., gt=0, le=365)):
    new_trans = Transaction(user_id)
    status_of_trans = await new_trans.check_status(transaction_id)
    if status_of_trans != 0:
        return {"rc": status_of_trans}
    token = generate_token(user_id)
    subscription = await extend_subscription(user_id, days, token)
    result_url = await generate_link(user_id, token)

    return {
        "rc": 0,
        "message": "Подписка оформлена",
        "token": token,
        "expires": subscription.expiration_date.date(),
        "url": result_url
    }

async def read_file(path: str) -> str:
    def _read():
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    return await asyncio.to_thread(_read)

@app.get("/api/configs/{user_id}")
async def get_config(user_id: int, token: str = Query(...)):
    is_active = await is_subscription_active(user_id, token)

    if not is_active:
        raise HTTPException(status_code=401)

    try:
        config_content = await read_file("config.txt")
    except FileNotFoundError:
        raise HTTPException(status_code=404)

    return PlainTextResponse(
        content=config_content,
        media_type="text/plain",
        headers={"Content-Disposition": "inline"}
    )

    




    