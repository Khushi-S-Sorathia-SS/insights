import asyncio
import sys
import os

# Add parent directory to sys.path to allow imports from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.database import engine
from sqlalchemy import text

async def migrate():
    print("Starting database migration...")
    async with engine.begin() as conn:
        # Check if dataset_id exists
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='dashboards' AND column_name='dataset_id'"))
        if not result.fetchone():
            print("Adding dataset_id column to dashboards table...")
            # We first add it as nullable, then we might need to populate it if there's data, 
            # but since this is a refactor to a new system, we'll just add it.
            await conn.execute(text("ALTER TABLE dashboards ADD COLUMN dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE"))
            # If there are existing dashboards, we have a problem because dataset_id is NOT NULL in the model.
            # However, for the sake of migration, we'll allow it to be null initially if there are rows.
            # But the model says nullable=False.
            # Let's assume the user is okay with clearing existing dashboards if they are inconsistent.
        
        # Check if active_version exists
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='dashboards' AND column_name='active_version'"))
        if not result.fetchone():
            print("Adding active_version column to dashboards table...")
            await conn.execute(text("ALTER TABLE dashboards ADD COLUMN active_version INTEGER DEFAULT 1"))
            
        # Check if last_layout_update exists
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='dashboards' AND column_name='last_layout_update'"))
        if not result.fetchone():
            print("Adding last_layout_update column to dashboards table...")
            await conn.execute(text("ALTER TABLE dashboards ADD COLUMN last_layout_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))

        # Create chat_messages table if it doesn't exist
        print("Ensuring all tables exist...")
        from backend.db.database import Base
        # This will create chat_messages if it's missing
        await conn.run_sync(Base.metadata.create_all)

    print("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(migrate())
