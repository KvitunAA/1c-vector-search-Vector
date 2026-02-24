# Профили проектов

Каждая подпапка — профиль для отдельной конфигурации 1С.

## Шаблон: your_project

- `your_project.env` — конфигурация (CONFIG_PATH, EMBEDDING_* и т.д.)
- `your_project.env.local` — переопределения для текущей машины (не коммитить)
- `ИнструкцияПоИспользованиюMCP.md` — описание инструментов для аналитика
- `MCP_SETUP.md` — инструкция подключения к Cursor

## Создание нового проекта

```cmd
python init_project.py -n my_project -c "D:\Path\To\1C\Config" --add-mcp --index -y
```

Или скопируйте `your_project` и переименуйте, затем отредактируйте `.env`.
