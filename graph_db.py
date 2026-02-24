"""
Графовая база данных для хранения связей между объектами конфигурации 1С.
Использует SQLite для персистентного хранения узлов и рёбер.
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import Config

logger = logging.getLogger(__name__)


class GraphDBManager:
    """Менеджер графовой БД для конфигурации 1С"""

    NODE_TYPES = ("Metadata", "Method", "Form")
    EDGE_TYPES = ("REFERENCES", "HAS_METHOD", "HAS_FORM", "ATTRIBUTE_TYPE", "USES_IN_CODE")

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or Config.GRAPHDB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
        logger.info(f"Графовая БД инициализирована: {self.db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                name TEXT NOT NULL,
                object_type TEXT,
                object_name TEXT,
                synonym TEXT,
                extra TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);
            CREATE INDEX IF NOT EXISTS idx_nodes_object ON nodes(object_type, object_name);

            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                extra TEXT,
                FOREIGN KEY (source_id) REFERENCES nodes(id),
                FOREIGN KEY (target_id) REFERENCES nodes(id)
            );
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type);
        """)
        conn.commit()

    def clear(self):
        """Очистка графа перед переиндексацией"""
        conn = self._get_conn()
        conn.execute("DELETE FROM edges")
        conn.execute("DELETE FROM nodes")
        conn.commit()
        logger.info("Граф очищен")

    def add_node(
        self,
        node_id: str,
        node_type: str,
        name: str,
        object_type: Optional[str] = None,
        object_name: Optional[str] = None,
        synonym: Optional[str] = None,
        extra: Optional[Dict] = None,
    ):
        """Добавление узла (upsert)"""
        if node_type not in self.NODE_TYPES:
            raise ValueError(f"Неизвестный тип узла: {node_type}")
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO nodes (id, node_type, name, object_type, object_name, synonym, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node_id,
                node_type,
                name,
                object_type,
                object_name,
                synonym,
                json.dumps(extra, ensure_ascii=False) if extra else None,
            ),
        )
        conn.commit()

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        extra: Optional[Dict] = None,
    ):
        """Добавление ребра (без дубликатов)"""
        if edge_type not in self.EDGE_TYPES:
            raise ValueError(f"Неизвестный тип ребра: {edge_type}")
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT 1 FROM edges WHERE source_id=? AND target_id=? AND edge_type=?",
            (source_id, target_id, edge_type),
        )
        if cur.fetchone():
            return
        conn.execute(
            """
            INSERT INTO edges (source_id, target_id, edge_type, extra)
            VALUES (?, ?, ?, ?)
            """,
            (
                source_id,
                target_id,
                edge_type,
                json.dumps(extra, ensure_ascii=False) if extra else None,
            ),
        )
        conn.commit()

    def ensure_metadata_node(self, object_type: str, object_name: str, synonym: str = "") -> str:
        """Создаёт узел метаданных, возвращает id"""
        node_id = f"metadata:{object_type}:{object_name}"
        self.add_node(
            node_id=node_id,
            node_type="Metadata",
            name=object_name,
            object_type=object_type,
            object_name=object_name,
            synonym=synonym,
        )
        return node_id

    def get_dependencies(self, object_name: str, max_depth: int = 2) -> List[Dict]:
        """Что зависит от объекта X (кто на него ссылается)."""
        conn = self._get_conn()
        cur = conn.execute(
            """
            SELECT DISTINCT n.id, n.name, n.object_type, n.object_name, e.edge_type
            FROM edges e
            JOIN nodes n ON n.id = e.source_id
            WHERE e.target_id LIKE ? OR e.target_id = ?
            ORDER BY e.edge_type, n.name
            LIMIT 100
            """,
            (f"%:{object_name}", f"metadata:%:{object_name}"),
        )
        return [
            {
                "object": f"{r['object_type'] or ''}.{r['object_name'] or r['name']}",
                "node_id": r["id"],
                "edge_type": r["edge_type"],
            }
            for r in cur.fetchall()
        ]

    def get_references(self, object_name: str) -> List[Dict]:
        """На что ссылается объект X (какие объекты он использует)."""
        conn = self._get_conn()
        cur = conn.execute(
            """
            SELECT DISTINCT n.id, n.name, n.object_type, n.object_name, e.edge_type
            FROM edges e
            JOIN nodes n ON n.id = e.target_id
            WHERE e.source_id LIKE ? OR e.source_id = ?
            ORDER BY e.edge_type, n.name
            LIMIT 100
            """,
            (f"%:{object_name}:%", f"metadata:%:{object_name}"),
        )
        return [
            {
                "object": f"{r['object_type'] or ''}.{r['object_name'] or r['name']}",
                "node_id": r["id"],
                "edge_type": r["edge_type"],
            }
            for r in cur.fetchall()
        ]

    def get_stats(self) -> Dict:
        """Статистика графа"""
        conn = self._get_conn()
        nodes_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edges_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        by_type = dict(
            conn.execute(
                "SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type"
            ).fetchall()
        )
        edge_by_type = dict(
            conn.execute(
                "SELECT edge_type, COUNT(*) FROM edges GROUP BY edge_type"
            ).fetchall()
        )
        return {
            "nodes_count": nodes_count,
            "edges_count": edges_count,
            "nodes_by_type": by_type,
            "edges_by_type": edge_by_type,
        }

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
