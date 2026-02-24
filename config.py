import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Определяем корневую директорию проекта
PROJECT_ROOT = Path(__file__).parent


def load_profile(profile_name: str = None):
    """
    Загружает конфигурацию профиля

    Args:
        profile_name: Имя профиля (например, 'your_project', 'gisu', 'erp')
                     Если None, используется переменная окружения PROJECT_PROFILE
                     или дефолтный профиль
    """
    if profile_name is None:
        profile_name = os.getenv("PROJECT_PROFILE", "default")

    profile_path = PROJECT_ROOT / "projects" / profile_name / f"{profile_name}.env"

    if not profile_path.exists():
        logger.warning(f"Профиль '{profile_name}' не найден по пути {profile_path}")
        logger.info("Используются переменные окружения по умолчанию")
    else:
        logger.info(f"Загружен профиль: {profile_name} из {profile_path}")
        load_dotenv(profile_path, override=True)

    profile_local = profile_path.parent / f"{profile_name}.env.local"
    if profile_local.exists():
        load_dotenv(profile_local, override=True)
        logger.info(f"Применены переопределения из {profile_local}")

    return profile_name


current_profile = load_profile()


class Config:
    """Настройки приложения"""

    PROFILE_NAME = current_profile
    PROFILE_DIR = PROJECT_ROOT / "projects" / current_profile

    CONFIG_PATH = os.getenv("CONFIG_PATH", "")
    VECTORDB_PATH = os.getenv(
        "VECTORDB_PATH",
        str(PROFILE_DIR / "vectordb")
    )
    GRAPHDB_PATH = os.getenv(
        "GRAPHDB_PATH",
        str(PROFILE_DIR / "graphdb" / "graph.db")
    )

    EMBEDDING_MODEL = os.getenv(
        "EMBEDDING_MODEL",
        "your-embedding-model-name"
    )
    EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))
    EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", "")
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "dummy")
    EMBEDDING_ADD_EOS_MANUAL = os.getenv("EMBEDDING_ADD_EOS_MANUAL", "false").lower() in ("true", "1", "yes")
    EMBEDDING_MAX_CHARS = int(os.getenv("EMBEDDING_MAX_CHARS", "0"))

    COLLECTION_CODE = "1c_code"
    COLLECTION_METADATA = "1c_metadata"
    COLLECTION_FORMS = "1c_forms"

    COLLECTIONS = {
        "code": COLLECTION_CODE,
        "metadata": COLLECTION_METADATA,
        "forms": COLLECTION_FORMS
    }

    METADATA_TYPES = {
        "Справочник": "Catalogs",
        "Документ": "Documents",
        "РегистрСведений": "InformationRegisters",
        "РегистрНакопления": "AccumulationRegisters",
        "РегистрБухгалтерии": "AccountingRegisters",
        "Обработка": "DataProcessors",
        "Отчет": "Reports",
        "ОбщийМодуль": "CommonModules",
        "Перечисление": "Enums",
        "ПланСчетов": "ChartsOfAccounts"
    }

    DEFAULT_SEARCH_LIMIT = int(os.getenv("DEFAULT_SEARCH_LIMIT", "5"))
    MAX_SEARCH_LIMIT = int(os.getenv("MAX_SEARCH_LIMIT", "20"))

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """Валидация конфигурации"""
        errors = []

        if not cls.CONFIG_PATH:
            errors.append("CONFIG_PATH не установлен")
        elif not Path(cls.CONFIG_PATH).exists():
            errors.append(f"Путь к конфигурации не существует: {cls.CONFIG_PATH}")

        if errors:
            logger.error("Ошибки конфигурации:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        logger.info(f"Конфигурация валидна для профиля '{cls.PROFILE_NAME}'")
        return True

    @classmethod
    def show(cls):
        """Показать текущую конфигурацию"""
        logger.info("=" * 60)
        logger.info(f"ПРОФИЛЬ: {cls.PROFILE_NAME}")
        logger.info("=" * 60)
        logger.info(f"Директория профиля: {cls.PROFILE_DIR}")
        logger.info(f"Путь к конфигурации 1С: {cls.CONFIG_PATH}")
        logger.info(f"Путь к векторной БД: {cls.VECTORDB_PATH}")
        logger.info(f"Путь к графовой БД: {cls.GRAPHDB_PATH}")
        logger.info(f"Модель эмбеддингов: {cls.EMBEDDING_MODEL}")
        logger.info(f"Размерность эмбеддингов: {cls.EMBEDDING_DIMENSION}")
        if cls.EMBEDDING_API_BASE:
            logger.info(f"API эмбеддингов: {cls.EMBEDDING_API_BASE}")
        if "Qwen3" in cls.EMBEDDING_MODEL:
            logger.info(f"EMBEDDING_ADD_EOS_MANUAL: {cls.EMBEDDING_ADD_EOS_MANUAL}")
        if cls.EMBEDDING_MAX_CHARS > 0:
            logger.info(f"EMBEDDING_MAX_CHARS (обрезание чанков): {cls.EMBEDDING_MAX_CHARS}")
        logger.info(f"Лимит поиска по умолчанию: {cls.DEFAULT_SEARCH_LIMIT}")
        logger.info(f"Максимальный лимит поиска: {cls.MAX_SEARCH_LIMIT}")
        logger.info(f"Уровень логирования: {cls.LOG_LEVEL}")
        logger.info("=" * 60)


logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=Config.LOG_LEVEL
)


if __name__ == "__main__":
    Config.show()
    Config.validate()
