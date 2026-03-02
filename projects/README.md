# Профили проектов

Каждая подпапка — профиль для отдельной конфигурации 1С.

## Шаблон: your_project

- `your_project.env` — конфигурация (CONFIG_PATH, EMBEDDING_* и т.д.)
- `your_project.env.local` — переопределения для текущей машины (не коммитить)
- `ИнструкцияПоИспользованиюMCP.md` — описание инструментов для аналитика
- `MCP_SETUP.md` — инструкция подключения к Cursor
- `MODEL_CONFIGURATION_RECOMMENDATIONS.md` — выбор моделей эмбеддингов (nomic, BGE-M3, Qwen3), настройка чанков и контекста по объёму RAM. **Qwen3 (LM Studio/GGUF):** `EMBEDDING_ADD_EOS_MANUAL=false` (по умолчанию — llama.cpp добавляет EOS автоматически)

## Скрипты индексации (корень репозитория)

| Скрипт | Назначение |
|--------|------------|
| `run_index_your_project.cmd` | Полная индексация: векторная БД + граф (код, метаданные, формы, граф связей) |
| `run_index_vector_your_project.cmd` | Только векторная БД: код, метаданные, формы (без графа) |
| `run_index_graph_your_project.cmd` | Только граф связей (без векторной БД) |

## Создание нового проекта

```cmd
python init_project.py -n my_project -c "D:\Path\To\1C\Config" --add-mcp --index -y
```

Или скопируйте `your_project` и переименуйте, затем отредактируйте `.env`.

---

## Текущие изменения (02.03.2026)

- **Структура профилей** — каждая подпапка `projects/<имя>/` содержит `.env`, `vectordb/`, `graphdb/` и документацию.
- **MODEL_CONFIGURATION_RECOMMENDATIONS.md** — рекомендации по выбору моделей эмбеддингов (nomic, BGE-M3, Qwen3), настройке чанков и контекста в зависимости от объёма RAM (8/16/32/48 GB).
- **Раздельная индексация** — `run_index_vector_*.cmd` (только векторная БД), `run_index_graph_*.cmd` (только граф). Полная индексация — `run_index_*.cmd` или `python run_indexer.py --clear` без `--vector-only`.
- **Поддержка вложенных путей** — профили вида `esty/osn` → `projects/esty/osn/osn.env`.
- **init_project.py** — создание нового проекта с `-n`, `-c`, `--add-mcp`, `--index`.
