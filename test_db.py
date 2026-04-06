import asyncio
from app.core.database import SessionLocal
from app.models import TemplateContract
from sqlalchemy import select

async def main():
    async with SessionLocal() as db:
        result = await db.execute(select(TemplateContract))
        templates = result.scalars().all()
        for t in templates:
            print(f"ID: {t.id}, Title: {t.title}")

if __name__ == "__main__":
    asyncio.run(main())
