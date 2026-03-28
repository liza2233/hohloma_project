from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from .bd_connect import AsyncSessionLocal
from .schemes import Subscription

async def is_validate_user(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
                Subscription.expiration_date > datetime.now(timezone.utc)
            )
        )

        return result.scalars().first()

async def is_subscription_active(user_id: int, token: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.token == token,
                Subscription.is_active == True,
                Subscription.expiration_date > datetime.now(timezone.utc)
            )
        )

        return result.scalars().first()


async def extend_subscription(user_id: int, days: int, token: str):
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)

        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True
            ).order_by(Subscription.expiration_date.desc())
        )

        subscription = result.scalars().first()

        if subscription:
            base_date = max(subscription.expiration_date, now)
            subscription.expiration_date = base_date + timedelta(days=days)

            if token:
                subscription.token = token

        else:
            subscription = Subscription(
                user_id=user_id,
                payment_date=now,
                expiration_date=now + timedelta(days=days),
                is_active=True,
                token=token
            )
            session.add(subscription)

        await session.commit()
        await session.refresh(subscription)

        return subscription