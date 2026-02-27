"""
Менеджер векторной базы данных для хранения информации о конфигурации 1С
"""
import logging
from typing import List, Dict, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from config import Config

logger = logging.getLogger(__name__)

QWEN3_EOS_SUFFIX = "<|endoftext|>"


class QwenEOSEmbeddingWrapper:
    """Обёртка для добавления EOS-токена Qwen3 при EMBEDDING_ADD_EOS_MANUAL=true."""

    def __init__(self, base_embedding_fn):
        self._base = base_embedding_fn

    def __call__(self, input: List[str]) -> List[List[float]]:
        texts_with_eos = [
            t if t.endswith(QWEN3_EOS_SUFFIX) else t + QWEN3_EOS_SUFFIX
            for t in input
        ]
        return self._base(texts_with_eos)

    def name(self) -> str:
        if hasattr(self._base, "name") and callable(self._base.name):
            return self._base.name()
        return "QwenEOSWrapper"


class VectorDBManager:
    """Управление векторной БД"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.VECTORDB_PATH
        Path(self.db_path).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )

        if Config.EMBEDDING_API_BASE:
            base_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_base=Config.EMBEDDING_API_BASE,
                api_key=Config.EMBEDDING_API_KEY,
                model_name=Config.EMBEDDING_MODEL
            )
            if "Qwen3" in Config.EMBEDDING_MODEL and Config.EMBEDDING_ADD_EOS_MANUAL:
                self.embedding_function = QwenEOSEmbeddingWrapper(base_ef)
                logger.info(
                    f"Эмбеддинги через API: {Config.EMBEDDING_API_BASE}, модель: {Config.EMBEDDING_MODEL} "
                    f"(добавлен EOS-суффикс вручную)"
                )
            else:
                self.embedding_function = base_ef
                logger.info(f"Эмбеддинги через API: {Config.EMBEDDING_API_BASE}, модель: {Config.EMBEDDING_MODEL}")
        else:
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=Config.EMBEDDING_MODEL,
                trust_remote_code=True
            )
            logger.info(f"Эмбеддинги локально: {Config.EMBEDDING_MODEL}")

        self.collections = {}
        self._init_collections()

        logger.info(f"Векторная БД инициализирована: {self.db_path}")

    def _init_collections(self):
        for key, name in Config.COLLECTIONS.items():
            try:
                self.collections[key] = self.client.get_or_create_collection(
                    name=name,
                    embedding_function=self.embedding_function,
                    metadata={"description": f"Коллекция для {key} из конфигурации 1С"}
                )
                logger.info(f"Коллекция '{name}' готова")
            except Exception as e:
                logger.error(f"Ошибка создания коллекции {name}: {e}")
                raise

    def clear_all_collections(self):
        for name in Config.COLLECTIONS.values():
            try:
                self.client.delete_collection(name=name)
                logger.info(f"Коллекция '{name}' удалена")
            except Exception as e:
                logger.warning(f"Не удалось удалить коллекцию {name}: {e}")
        self._init_collections()

    def add_code_chunks(self, chunks: List[Dict], batch_size: int = 100):
        collection = self.collections["code"]
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            documents = []
            metadatas = []
            ids = []
            for j, chunk in enumerate(batch):
                text_parts = []
                if chunk.get("comments"):
                    text_parts.append("// " + "\n// ".join(chunk["comments"]))
                text_parts.append(chunk["signature"])
                text_parts.append(chunk["code"])
                document = "\n".join(text_parts)
                if Config.EMBEDDING_MAX_CHARS > 0 and len(document) > Config.EMBEDDING_MAX_CHARS:
                    document = document[: Config.EMBEDDING_MAX_CHARS - 3] + "..."
                documents.append(document)
                metadata = {
                    "object_name": chunk.get("object_name", ""),
                    "module_name": chunk.get("module_name", ""),
                    "method_name": chunk.get("method_name", ""),
                    "method_type": chunk.get("method_type", ""),
                    "is_export": chunk.get("is_export", False),
                    "signature": chunk.get("signature", ""),
                    "file_path": chunk.get("file_path", "")
                }
                metadatas.append(metadata)
                chunk_id = f"code_{i + j}_{chunk.get('method_name', 'unknown')}"
                ids.append(chunk_id)
            try:
                collection.add(documents=documents, metadatas=metadatas, ids=ids)
                logger.info(f"Добавлено {len(batch)} чанков кода (батч {i // batch_size + 1})")
            except Exception as e:
                logger.error(f"Ошибка добавления кода в БД: {e}")

    def add_metadata_objects(self, metadata_objects: List[Dict], batch_size: int = 50):
        collection = self.collections["metadata"]
        for i in range(0, len(metadata_objects), batch_size):
            batch = metadata_objects[i:i + batch_size]
            documents = []
            metadatas = []
            ids = []
            for j, obj in enumerate(batch):
                text_parts = [
                    f"Тип: {obj.get('type', '')}",
                    f"Имя: {obj.get('name', '')}",
                    f"Синоним: {obj.get('synonym', '')}",
                    f"Комментарий: {obj.get('comment', '')}"
                ]
                if obj.get('attributes'):
                    attr_list = [f"{attr['name']} ({attr['type']})" for attr in obj['attributes']]
                    text_parts.append(f"Реквизиты: {', '.join(attr_list)}")
                if obj.get('tabular_sections'):
                    text_parts.append(f"Табличные части: {', '.join(obj['tabular_sections'])}")
                document = "\n".join(text_parts)
                if Config.EMBEDDING_MAX_CHARS > 0 and len(document) > Config.EMBEDDING_MAX_CHARS:
                    document = document[: Config.EMBEDDING_MAX_CHARS - 3] + "..."
                documents.append(document)
                metadata = {
                    "object_name": obj.get('name', ''),
                    "object_type": obj.get('type', ''),
                    "synonym": obj.get('synonym', ''),
                    "description": obj.get('comment', ''),
                    "has_modules": ','.join(obj.get('has_modules', [])),
                    "attributes_count": obj.get('attributes_count', 0),
                    "file_path": obj.get('file_path', '')
                }
                metadatas.append(metadata)
                obj_id = f"metadata_{obj.get('type', 'unknown')}_{obj.get('name', 'unknown')}_{i + j}"
                ids.append(obj_id)
            try:
                collection.add(documents=documents, metadatas=metadatas, ids=ids)
                logger.info(f"Добавлено {len(batch)} объектов метаданных (батч {i // batch_size + 1})")
            except Exception as e:
                logger.error(f"Ошибка добавления метаданных в БД: {e}")

    def add_forms(self, forms: List[Dict], batch_size: int = 50):
        collection = self.collections["forms"]
        for i in range(0, len(forms), batch_size):
            batch = forms[i:i + batch_size]
            documents = []
            metadatas = []
            ids = []
            for j, form in enumerate(batch):
                text_parts = [
                    f"Форма: {form.get('form_name', '')}",
                    f"Объект: {form.get('object_type', '')} {form.get('object_name', '')}"
                ]
                if form.get('elements'):
                    text_parts.append(f"Элементы: {', '.join(form['elements'][:20])}")
                document = "\n".join(text_parts)
                if Config.EMBEDDING_MAX_CHARS > 0 and len(document) > Config.EMBEDDING_MAX_CHARS:
                    document = document[: Config.EMBEDDING_MAX_CHARS - 3] + "..."
                documents.append(document)
                metadata = {
                    "form_name": form.get('form_name', ''),
                    "object_name": form.get('object_name', ''),
                    "object_type": form.get('object_type', ''),
                    "elements_count": form.get('elements_count', 0),
                    "file_path": form.get('file_path', '')
                }
                metadatas.append(metadata)
                form_id = f"form_{form.get('object_name', 'unknown')}_{form.get('form_name', 'unknown')}_{i + j}"
                ids.append(form_id)
            try:
                collection.add(documents=documents, metadatas=metadatas, ids=ids)
                logger.info(f"Добавлено {len(batch)} форм (батч {i // batch_size + 1})")
            except Exception as e:
                logger.error(f"Ошибка добавления форм в БД: {e}")

    def search_code(self, query: str, limit: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        collection = self.collections["code"]
        try:
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=filters if filters else None
            )
            return self._format_results(results)
        except Exception as e:
            logger.error(f"Ошибка поиска в коде: {e}")
            return []

    def search_code_by_object(
        self,
        object_name: str,
        query: Optional[str] = None,
        limit: int = 200
    ) -> List[Dict]:
        collection = self.collections["code"]
        search_query = query if query else object_name
        try:
            results = collection.query(
                query_texts=[search_query],
                n_results=limit,
                where={"object_name": {"$eq": object_name}}
            )
            return self._format_results(results)
        except Exception as e:
            logger.error(f"Ошибка поиска кода по объекту '{object_name}': {e}")
            return []

    def search_metadata(self, query: str, limit: int = 5, object_type: Optional[str] = None) -> List[Dict]:
        collection = self.collections["metadata"]
        where_filter = {"object_type": object_type} if object_type else None
        try:
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter
            )
            return self._format_results(results)
        except Exception as e:
            logger.error(f"Ошибка поиска в метаданных: {e}")
            return []

    def search_forms(self, query: str, limit: int = 5) -> List[Dict]:
        collection = self.collections["forms"]
        try:
            results = collection.query(
                query_texts=[query],
                n_results=limit
            )
            return self._format_results(results)
        except Exception as e:
            logger.error(f"Ошибка поиска форм: {e}")
            return []

    def _format_results(self, results) -> List[Dict]:
        formatted = []
        if not results['documents'] or not results['documents'][0]:
            return formatted
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            formatted.append({
                "rank": i + 1,
                "relevance": round(1 - distance, 3),
                "document": doc,
                "metadata": metadata
            })
        return formatted

    def get_stats(self) -> Dict:
        stats = {}
        for key, collection in self.collections.items():
            try:
                stats[key] = collection.count()
            except Exception:
                stats[key] = 0
        return stats
