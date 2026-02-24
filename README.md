# 1c-vector-search MCP Server

MCP-сервер для семантического поиска по коду и метаданным конфигураций 1С (КА, ЗУП, УТ, ERP и т.п.). Работает локально через ChromaDB и SQLite, без Docker.

## Состав проекта

- **Python-модули** — полная реализация MCP-сервера, индексатора и графа зависимостей:
  - `server.py` — MCP-сервер (stdio-транспорт для Cursor)
  - `config.py` — загрузка конфигурации из профилей
  - `vectordb_manager.py` — работа с ChromaDB
  - `graph_db.py` — граф зависимостей (SQLite)
  - `parser_1c.py` — парсер BSL и XML метаданных 1С
  - `index_config.py` — индексация кода, метаданных, форм и графа
  - `index_graph.py` — индексация только графа
  - `run_server.py`, `run_indexer.py` — точки входа
- **Профили** — `projects/your_project/` — шаблон с обезличенными параметрами
- **Скрипты** — `run_server_your_project.cmd`, `run_index_your_project.cmd`, `run_index_graph_your_project.cmd`
- **Схемы MCP** — `SERVER_METADATA.json`, `tools/*.json` — описание инструментов для клиентов

## Быстрый старт

### 1. Установка зависимостей

```cmd
cd 1c-vector-search-KA_Vector
pip install -r requirements.txt
```

### 2. Настройка профиля

1. Переименуйте `projects/your_project` в `projects/<имя_проекта>` (например, `KA_Vector`).
2. Переименуйте `your_project.env` в `<имя>.env`.
3. Отредактируйте `.env`:
   - **CONFIG_PATH** — путь к выгрузке конфигурации 1С (корень, где лежит `Configuration.xml`)
   - **EMBEDDING_API_BASE** — URL API эмбеддингов (LM Studio, LocalAI и т.д.), или оставьте пустым для локальной модели
   - **EMBEDDING_MODEL** — имя модели эмбеддингов
   - **EMBEDDING_DIMENSION** — размерность векторов (768 для nomic, 4096 для Qwen3 и т.п.)

### 3. Переименование скриптов (опционально)

Переименуйте `run_server_your_project.cmd` → `run_server_<имя>.cmd` и аналогично `run_index_*.cmd`, `run_index_graph_*.cmd`. Либо используйте `init_project.py` для создания нового проекта.

### 4. Индексация

```cmd
run_index_your_project.cmd
```

Или через Python:

```cmd
set PROJECT_PROFILE=your_project
python run_indexer.py --clear
```

### 5. Подключение в Cursor

`Ctrl+Shift+P` → **"MCP: Edit Config File"**

Добавьте в `mcpServers` (замените пути на актуальные):

```json
"1c-vector-search": {
  "command": "cmd",
  "args": ["/c", "C:\\path\\to\\1c-vector-search-KA_Vector\\run_server_your_project.cmd"],
  "env": {
    "PROJECT_PROFILE": "your_project",
    "VECTORDB_PATH": "C:\\path\\to\\1c-vector-search-KA_Vector\\projects\\your_project\\vectordb",
    "GRAPHDB_PATH": "C:\\path\\to\\1c-vector-search-KA_Vector\\projects\\your_project\\graphdb\\graph.db"
  },
  "description": "MCP сервер для семантического поиска по конфигурации 1С"
}
```

### 6. Запуск MCP

Cursor запускает MCP-сервер автоматически при обращении к инструментам. Для проверки можно запустить вручную:

```cmd
run_server_your_project.cmd
```

## Обезличенные параметры

В шаблоне используются плейсхолдеры:

- **CONFIG_PATH** — `C:\path\to\your\1c\config`
- **EMBEDDING_API_BASE** — `http://your-host:port/v1`
- **EMBEDDING_MODEL** — `your-embedding-model-name`
- **VECTOR_PYTHON_PATH** (в `local.env`) — `C:\path\to\python.exe`

Файлы `*.env.local` и `local.env` не коммитятся в Git.

## Перенос на другую машину

См. [PORTABILITY.md](PORTABILITY.md) — использование `setup_machine.py`, переопределение путей в `*.env.local`.

## Инструменты (tools)

- `search_1c_code` — семантический поиск по коду 1С
- `search_1c_metadata` — поиск объектов метаданных
- `search_1c_forms` — поиск форм
- `search_by_object_name` — полная информация по объекту
- `find_1c_method_usage` — поиск мест использования метода
- `graph_dependencies`, `graph_references`, `graph_stats` — анализ графа зависимостей
- `get_vectordb_stats` — статистика векторной БД
- `get_analyst_instructions` — инструкция для аналитика

Подробное описание — в `projects/your_project/ИнструкцияПоИспользованиюMCP.md`.
