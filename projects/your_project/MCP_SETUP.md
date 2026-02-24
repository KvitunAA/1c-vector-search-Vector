# Подключение your_project к MCP в Cursor

## Шаги настройки

1. **Переименуйте профиль** — замените `your_project` на имя вашего проекта (например, `KA_Vector`).
2. **Настройте `your_project.env`** — укажите `CONFIG_PATH` (путь к выгрузке конфигурации 1С) и параметры эмбеддингов.
3. **Переименуйте .cmd-скрипты** — `run_server_your_project.cmd` → `run_server_<имя>.cmd` и т.д., либо используйте `init_project.py` для создания нового проекта.

## Подключение в Cursor

`Ctrl+Shift+P` → **"MCP: Edit Config File"**

В секцию `mcpServers` добавьте (замените пути на актуальные):

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

## Индексация

```cmd
run_index_your_project.cmd
```

Для индексации только графа (без векторной БД):

```cmd
run_index_graph_your_project.cmd
```

## Использование

Префикс @ при выборе MCP: `@1c-vector-search`
