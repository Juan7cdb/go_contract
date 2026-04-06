
import asyncio
from sqlalchemy import text
from app.core.database import async_session_maker
from app.models import User

async def test_conn():
    print("Testing connection...")
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = result.scalars().all()
            print(f"Tables found: {tables}")
            
            # Check if users table exists and columns
            result = await session.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users'"))
            cols = result.all()
            print(f"Users table columns: {cols}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
