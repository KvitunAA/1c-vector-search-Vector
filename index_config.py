"""
Скрипт индексации конфигурации 1С в векторную БД
"""
import logging
import sys
from pathlib import Path
from typing import List, Dict
import argparse
from tqdm import tqdm

from config import Config
from parser_1c import ConfigurationScanner, BSLParser
from vectordb_manager import VectorDBManager
from graph_db import GraphDBManager

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('indexing.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ConfigIndexer:
    """Индексатор конфигурации 1С"""

    def __init__(self, config_path: str, db_path: str = None, clear_existing: bool = False):
        self.config_path = Path(config_path)
        self.scanner = ConfigurationScanner(self.config_path)
        self.db_manager = VectorDBManager(db_path)

        if clear_existing:
            logger.info("Очистка существующей векторной БД...")
            self.db_manager.clear_all_collections()

    def index_all(self):
        """Полная индексация конфигурации"""
        logger.info("=" * 80)
        logger.info("Начало индексации конфигурации 1С")
        logger.info(f"Путь к конфигурации: {self.config_path}")
        logger.info("=" * 80)

        logger.info("\n[1/4] Индексация модулей и кода...")
        code_chunks = self._index_code()

        logger.info("\n[2/4] Индексация метаданных объектов...")
        metadata_count = self._index_metadata()

        logger.info("\n[3/4] Индексация форм...")
        forms_count = self._index_forms()

        logger.info("\n[4/4] Индексация графа связей...")
        graph_stats = self._index_graph()

        logger.info("\n" + "=" * 80)
        logger.info("Индексация завершена!")
        logger.info("=" * 80)
        logger.info(f"Проиндексировано кода: {code_chunks} чанков")
        logger.info(f"Проиндексировано метаданных: {metadata_count} объектов")
        logger.info(f"Проиндексировано форм: {forms_count}")
        logger.info(f"Граф: {graph_stats.get('nodes_count', 0)} узлов, {graph_stats.get('edges_count', 0)} рёбер")

        stats = self.db_manager.get_stats()
        logger.info("\nСтатистика векторной БД:")
        for collection, count in stats.items():
            logger.info(f"  {collection}: {count} записей")

        logger.info("\n✅ Конфигурация готова к использованию!")

    def _index_code(self) -> int:
        """Индексация кода модулей"""
        logger.info("Сканирование BSL модулей...")
        modules_data = self.scanner.scan_all_modules()

        if not modules_data:
            logger.warning("Не найдено ни одного BSL модуля!")
            return 0

        logger.info(f"Найдено {len(modules_data)} файлов с кодом")

        all_chunks = []

        for file_path, object_full_name, methods in tqdm(modules_data, desc="Обработка модулей"):
            parts = object_full_name.split('.')
            object_type = parts[0] if len(parts) > 0 else "Unknown"
            object_name = parts[1] if len(parts) > 1 else "Unknown"
            module_name = file_path.stem

            for method in methods:
                chunk = {
                    "object_name": object_name,
                    "object_type": object_type,
                    "module_name": module_name,
                    "method_name": method["method_name"],
                    "method_type": method["method_type"],
                    "signature": method["signature"],
                    "is_export": method["is_export"],
                    "code": method["code"],
                    "comments": method.get("comments", []),
                    "file_path": str(file_path)
                }
                all_chunks.append(chunk)

        logger.info(f"Добавление {len(all_chunks)} чанков кода в векторную БД...")
        self.db_manager.add_code_chunks(all_chunks)

        return len(all_chunks)

    def _index_metadata(self) -> int:
        """Индексация метаданных"""
        logger.info("Сканирование метаданных объектов...")
        metadata_objects = self.scanner.scan_all_metadata()

        if not metadata_objects:
            logger.warning("Не найдено объектов метаданных!")
            return 0

        logger.info(f"Найдено {len(metadata_objects)} объектов метаданных")
        logger.info(f"Добавление {len(metadata_objects)} объектов в векторную БД...")
        self.db_manager.add_metadata_objects(metadata_objects)

        return len(metadata_objects)

    def _index_forms(self) -> int:
        """Индексация форм"""
        logger.info("Сканирование форм...")
        forms = self.scanner.scan_all_forms()

        if not forms:
            logger.warning("Не найдено форм!")
            return 0

        logger.info(f"Найдено {len(forms)} форм")
        logger.info(f"Добавление {len(forms)} форм в векторную БД...")
        self.db_manager.add_forms(forms)

        return len(forms)

    def _index_graph(self) -> Dict:
        """Индексация графа связей между объектами"""
        try:
            from index_graph import GraphIndexer
            graph_path = Path(Config.GRAPHDB_PATH).parent
            graph_path.mkdir(parents=True, exist_ok=True)
            graph_indexer = GraphIndexer(
                config_path=str(self.config_path),
                db_path=Config.GRAPHDB_PATH,
                clear_existing=True,
            )
            graph_indexer.index_all()
            return graph_indexer.graph.get_stats()
        except Exception as e:
            logger.warning(f"Ошибка индексации графа (продолжаем): {e}")
            return {"nodes_count": 0, "edges_count": 0}


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description='Индексация конфигурации 1С в векторную БД для MCP сервера'
    )
    parser.add_argument(
        '--config-path',
        type=str,
        default=Config.CONFIG_PATH,
        help=f'Путь к выгрузке конфигурации 1С (по умолчанию: {Config.CONFIG_PATH})'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default=Config.VECTORDB_PATH,
        help=f'Путь к векторной БД (по умолчанию: {Config.VECTORDB_PATH})'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Очистить существующую БД перед индексацией'
    )

    args = parser.parse_args()

    config_path = Path(args.config_path)
    if not config_path.exists():
        logger.error(f"Путь к конфигурации не найден: {args.config_path}")
        logger.error("Укажите правильный путь через --config-path")
        sys.exit(1)

    if not (config_path / "Configuration.xml").exists():
        logger.error(f"Не найден Configuration.xml в {args.config_path}")
        logger.error("Убедитесь, что указан путь к корню выгрузки конфигурации 1С")
        sys.exit(1)

    try:
        indexer = ConfigIndexer(
            config_path=args.config_path,
            db_path=args.db_path,
            clear_existing=args.clear
        )
        indexer.index_all()
    except KeyboardInterrupt:
        logger.warning("\nИндексация прервана пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ошибка при индексации: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
