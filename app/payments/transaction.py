import httpx
import asyncio
from .api_configs import APIConfig
import time

class Transaction:
    def __init__(self, id):
        self.configs = APIConfig()
        self.id = id
    

    async def get_link(self, pay_meth: int, amount: float, currency: str): 
        """
        pay_meth - Номер способа оплаты (к примеру, 2 для QR СБП) | Allowed values:  2 - СБП (QR-код), 3 - ЕРИП, 11 - Карточный эквайринг, 12 - международная оплата, 13 - Криптовалюта
        amount - Сумма платежа
        curency - Валюта платежа (например, RUB)
        description - Назначение (описание) платежа, указывайте по возможности всегда

        Возвращает dict
        В поле text:
        Время на оплату
        Сумму к оплате
        Ссылку для оплаты

        В поле transactionId:
        ID транзакции для получения статуса
        """
        description = f"Описание назначение платежа для пользователя с userid: {self.id}"
        endpoint = "transaction/process"
        url = f"{self.configs.base_url}{endpoint}"
        data = {
            "paymentMethod": pay_meth,
            "paymentDetails": {"amount": amount, "currency": currency},
            "description": description
        }
        async with httpx.AsyncClient(headers = self.configs.headers, timeout = self.configs.timeout) as client:
            try:
                r = await client.post(url=url, json = data)
                result_json = r.json()
                result = {"text": [
                    f"Время на оплату: {result_json['expiresIn']}",
                    f"Сумма к оплате: {result_json['paymentDetails']}",
                    f"Ссылка для оплаты:{result_json['redirect']}",
                ], "transaction_id": result_json['transactionId']
                }
                return result
            except Exception as e:
                print(e)


    async def check_status (self, transaction_id, max_time: int = 600, interval: float = 2.0 ):
        """
        Проверяет статус транзакции до получения финального состояния
        transaction_id: ID транзакции, получается из поля transaction_id функции get_link
        interval: перерыв между проверками статуса
        max_time: Время после которого возвращается статус 3 - Истекло время ожидания

        Функция возвращает 4 значения(int):
        0 - Транзакция подтверждена
        1 - Транзация отменена
        2 - Был выполнен возврат средств
        3 - истекло время ожидания выполнения платежа

        Пример использования:

        new_trans = Transaction(12) - id Юзера ТГ
        result = await new_trans.get_link(2, 200, "RUB", "Hello") - 
        trans_id = result["transaction_id"] 
        await new_trans.check_status(trans_id)
        """

        self.transaction_id=transaction_id
        endpoint = f"transaction/{transaction_id}"
        url = f"{self.configs.base_url}{endpoint}"
        start_time = time.time()
        async with httpx.AsyncClient(headers=self.configs.headers, timeout = self.configs.timeout) as client:
            while time.time() - start_time < max_time:
                try:
                    r = await client.get(url = url)
                    result_json = r.json()
                    status = result_json["status"]
                    print(status)
                    if status == "CONFIRMED":
                        return 0
                    elif status == "CANCELED":
                        return 1
                    elif status == "CHARGEBACKED":
                        return 2
                    elif status == "PENDING":
                        await asyncio.sleep(interval)
                except Exception as e:
                    print(e)
        return 3

