import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context

# 👇 Подключаем корень проекта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 👇 Импортируем из проекта
from database import DATABASE_URL
from models import Base
target_metadata = Base.metadata

# Alembic Config
config = context.config
fileConfig(config.config_file_name)

# Устанавливаем URL из database.py
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# 👇 Метаданные для автогенерации
target_metadata = Base.metadata

# ----------- 🔧 Асинхронные функции миграции -----------
def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Включить сравнение типов колонок
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations in 'online' mode (asyncpg engine)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    connectable = create_async_engine(DATABASE_URL, poolclass=None)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# 👇 Выбираем режим в зависимости от CLI
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
