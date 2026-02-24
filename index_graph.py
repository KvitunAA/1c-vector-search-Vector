"""
Скрипт индексации графа связей конфигурации 1С.
Строит граф: узлы (метаданные, методы, формы) и рёбра (REFERENCES, HAS_METHOD, HAS_FORM).
"""
import logging
import sys
from pathlib import Path

from config import Config
from graph_db import GraphDBManager
from parser_1c import BSLParser, ConfigurationScanner

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("indexing.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class GraphIndexer:
    """Индексатор графа конфигурации 1С"""

    def __init__(self, config_path: str, db_path: str = None, clear_existing: bool = False):
        self.config_path = Path(config_path)
        self.scanner = ConfigurationScanner(self.config_path)
        self.graph = GraphDBManager(db_path)

        if clear_existing:
            logger.info("Очистка существующего графа...")
            self.graph.clear()

    def index_all(self):
        """Полная индексация графа"""
        logger.info("=" * 60)
        logger.info("Начало индексации графа конфигурации 1С")
        logger.info(f"Путь к конфигурации: {self.config_path}")
        logger.info("=" * 60)

        metadata_list = self.scanner.scan_all_metadata()
        modules_data = self.scanner.scan_all_modules()
        forms_list = self.scanner.scan_all_forms()

        known_objects = {(m.get("object_type_dir", ""), m.get("name", "")) for m in metadata_list}

        for m in metadata_list:
            obj_type = m.get("object_type_dir", "Unknown")
            obj_name = m.get("name", "")
            self.graph.ensure_metadata_node(
                object_type=obj_type,
                object_name=obj_name,
                synonym=m.get("synonym", ""),
            )

        for file_path, object_full_name, methods in modules_data:
            parts = object_full_name.split(".")
            obj_type = parts[0] if len(parts) > 0 else "Unknown"
            obj_name = parts[1] if len(parts) > 1 else file_path.stem
            source_id = self.graph.ensure_metadata_node(obj_type, obj_name, "")

            for method in methods:
                method_name = method.get("method_name", "")
                module_name = file_path.stem
                method_id = f"method:{obj_type}:{obj_name}:{module_name}:{method_name}"
                self.graph.add_node(
                    node_id=method_id,
                    node_type="Method",
                    name=method_name,
                    object_type=obj_type,
                    object_name=obj_name,
                    extra={"module": module_name, "signature": method.get("signature", "")},
                )
                self.graph.add_edge(source_id, method_id, "HAS_METHOD")

                refs = BSLParser.extract_metadata_references_from_code(method.get("code", ""))
                for ref_type, ref_name in refs:
                    if (ref_type, ref_name) in known_objects or ref_type in (
                        "Catalogs",
                        "Documents",
                        "InformationRegisters",
                        "AccumulationRegisters",
                        "CommonModules",
                        "Enums",
                        "DataProcessors",
                        "Reports",
                    ):
                        target_id = self.graph.ensure_metadata_node(ref_type, ref_name, "")
                        self.graph.add_edge(source_id, target_id, "USES_IN_CODE")

        for form in forms_list:
            obj_type = form.get("object_type", "Unknown")
            obj_name = form.get("object_name", "")
            form_name = form.get("form_name", "")
            source_id = self.graph.ensure_metadata_node(obj_type, obj_name, "")
            form_id = f"form:{obj_type}:{obj_name}:{form_name}"
            self.graph.add_node(
                node_id=form_id,
                node_type="Form",
                name=form_name,
                object_type=obj_type,
                object_name=obj_name,
                extra={"elements_count": form.get("elements_count", 0)},
            )
            self.graph.add_edge(source_id, form_id, "HAS_FORM")

        stats = self.graph.get_stats()
        logger.info("=" * 60)
        logger.info("Индексация графа завершена!")
        logger.info("=" * 60)
        logger.info(f"Узлов: {stats['nodes_count']}, рёбер: {stats['edges_count']}")
        logger.info(f"По типам узлов: {stats['nodes_by_type']}")
        logger.info(f"По типам рёбер: {stats['edges_by_type']}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Индексация графа конфигурации 1С")
    parser.add_argument(
        "--config-path",
        type=str,
        default=Config.CONFIG_PATH,
        help="Путь к выгрузке конфигурации 1С",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Путь к файлу графовой БД (по умолчанию из конфига)",
    )
    parser.add_argument("--clear", action="store_true", help="Очистить граф перед индексацией")

    args = parser.parse_args()

    config_path = Path(args.config_path)
    if not config_path.exists():
        logger.error(f"Путь к конфигурации не найден: {args.config_path}")
        sys.exit(1)

    try:
        indexer = GraphIndexer(
            config_path=str(config_path),
            db_path=args.db_path,
            clear_existing=args.clear,
        )
        indexer.index_all()
    except Exception as e:
        logger.error(f"Ошибка при индексации графа: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
