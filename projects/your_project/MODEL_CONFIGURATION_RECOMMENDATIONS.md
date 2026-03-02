# Рекомендации по настройке моделей для 1c-vector-search

Документ содержит рекомендации по выбору моделей эмбеддингов, настройке чанков и контекста в зависимости от конфигурации ПК и требований к точности индексации конфигурации 1С.

---

## 1. Сравнение моделей эмбеддингов

### 1.1 Nomic: v1.5 vs v2-moe

| Характеристика | nomic-embed-text-v1.5 | nomic-embed-text-v2-moe |
|----------------|----------------------|--------------------------|
| **Архитектура** | Трансформер | Mixture-of-Experts (MoE) |
| **Параметры** | 137M | 475M всего, ~305M активных |
| **Контекст** | **8192 токенов** | **512 токенов** |
| **Размерность** | 768 (Matryoshka 64–768) | 768 (Matryoshka 256–768) |
| **Языки** | В основном английский | 100+ языков |
| **MTEB** | 62.28 | — |
| **Binary embeddings** | Да | Нет |

**Для 1С:** v1.5 предпочтительнее при 16+ GB RAM — длинный контекст (8192) позволяет целиком индексировать процедуры BSL. v2-moe — для слабого ПК (8 GB) через API или при мультиязычном поиске.

### 1.2 Сводная таблица моделей

| Модель | Контекст | Размерность | RAM (оценка) | Особенности |
|--------|----------|-------------|--------------|-------------|
| **nomic-embed-text-v1.5** | 8192 | 768 | ~1–2 GB | MTEB 62.28, Matryoshka, binary |
| **nomic-embed-text-v1** | 8192 | 768 | ~1–2 GB | Аналог v1.5 |
| **nomic-embed-text-v2-moe** | 512 | 768 | ~2–3 GB | 100+ языков, MoE |
| **BGE-M3** | 8192 | 1024 | ~5–9 GB | 100+ языков, fp16 экономит память |
| **Qwen3-Embedding-0.6B** | 32K | 1024 | ~2–3 GB | 32K контекст, 100+ языков |
| **Qwen3-Embedding-4B** | 32K | 2560 | ~8–12 GB | MTEB ~68+ |
| **Qwen3-Embedding-8B** | 32K | 4096 | ~16–24 GB | MTEB 70.58 (лидер) |
| **Granite Embedding R2** | 8192 | 768 | ~1–2 GB | Только английский |
| **paraphrase-multilingual-MiniLM-L12-v2** | 512 | 384 | ~0.5 GB | Лёгкая, 100+ языков |

---

## 2. Конфигурации ПК и рекомендуемые модели

### 2.1 Слабый ПК (8 GB RAM, без GPU)

| Компонент | Рекомендация | Альтернатива |
|-----------|--------------|--------------|
| **Эмбеддинги** | LM Studio / LocalAI (удалённый API) | sentence-transformers: `paraphrase-multilingual-MiniLM-L12-v2` (~420 MB) |
| **Модель эмбеддингов** | nomic-embed-text-v2-moe (512 токенов) | MiniLM-L12 (512 токенов) |
| **LLM для RAG** | Qwen2.5-1.5B-Instruct (Q4_K_M) ~2.5 GB RAM | Qwen2.5-0.5B при нехватке RAM |

**Ограничения:** Локальный запуск embedding + LLM одновременно может перегрузить память. Рекомендуется API на другом хосте или только embedding локально.

---

### 2.2 Средний ПК (16 GB RAM, опционально GPU 4–6 GB)

| Компонент | Рекомендация | Альтернатива |
|-----------|--------------|--------------|
| **Эмбеддинги** | Локально: sentence-transformers | LM Studio / LocalAI |
| **Модель эмбеддингов** | nomic-embed-text-v1.5 (8192 токена) | nomic-embed-text-v1, Qwen3-Embedding-0.6B |
| **LLM для RAG** | Qwen2.5-3B или 7B (Q4) | Phi-2, Mistral-7B |

---

### 2.3 Мощный ПК (32 GB RAM, GPU 8+ GB)

| Компонент | Рекомендация | Альтернатива |
|-----------|--------------|--------------|
| **Эмбеддинги** | BGE-M3 или Qwen3-Embedding-4B | nomic-embed-text-v1.5 |
| **LLM для RAG** | Qwen2.5-7B, Llama-3-8B, Mistral-7B | — |

---

### 2.4 Максимальная точность (48+ GB RAM или GPU 16+ GB)

| Компонент | Рекомендация |
|-----------|--------------|
| **Эмбеддинги** | Qwen3-Embedding-8B (MTEB 70.58) |
| **LLM для RAG** | Qwen2.5-7B, Llama-3-8B, Mistral-7B |

**Ресурсы для максимальной точности индексации 1С:**

| Компонент | Минимум | Оптимально | Максимум |
|-----------|---------|------------|----------|
| **RAM (embedding)** | 2 GB (nomic v1.5) | 8–16 GB (BGE-M3, Qwen3-0.6B) | 24–32 GB (Qwen3-8B) |
| **RAM (индексация)** | +2–4 GB | +4–8 GB | +8–16 GB |
| **Векторная БД** | ~3 KB × кол-во чанков | 50K чанков ≈ 150 MB | 200K чанков ≈ 600 MB |
| **Итого RAM** | 8 GB | 16–24 GB | 32–48 GB |

**Оценка объёма конфигурации 1С:** малая (ЗУП, УТ) ~5–15K процедур; средняя (ERP) ~30–80K; крупная с доработками 100K+.

---

## 3. Настройка чанков и контекста

### 3.1 Общие принципы для 1С (BSL)

- **Граница чанка** — процедура/функция (семантическая единица).
- **Коэффициент BSL:** ~2.0 симв/токен (кириллица, длинные идентификаторы).
- **Типичная процедура:** 30–80 строк ≈ 1500–4000 символов ≈ 750–2000 токенов.
- **Для максимальной точности:** контекст ≥ 8192 токенов позволяет целиком индексировать большинство процедур BSL.

### 3.2 Рекомендуемые значения по модели эмбеддингов

| Модель | Context length | EMBEDDING_MAX_TOKENS | EMBEDDING_MAX_CHARS | CHUNK_MAX_TOKENS | CHUNK_OVERLAP_TOKENS | EMBEDDING_DIMENSION |
|--------|----------------|----------------------|---------------------|------------------|----------------------|---------------------|
| **nomic-embed-text-v2-moe** | 512 | 512 | 1024 | 512 | 100 | 768 |
| **nomic-embed-text-v1** / **v1.5** | 8192 | 1024 | 2048 | 1024 | 100 | 768 |
| **BGE-M3** | 8192 | 1024 | 2048 | 1024 | 100 | 1024 |
| **Qwen3-Embedding-0.6B** | 32K | 2048 | 4096 | 2048 | 150 | 1024 |
| **Qwen3-Embedding-4B** | 32K | 2048 | 4096 | 2048 | 150 | 2560 |
| **Qwen3-Embedding-8B** | 32K | 2048 | 4096 | 2048–4096 | 150 | 4096 |
| **paraphrase-multilingual-MiniLM-L12-v2** | 512 | 512 | 1024 | 512 | 100 | 384 |
| **Granite Embedding R2** | 8192 | 1024 | 2048 | 1024 | 100 | 768 |

**Qwen3 через LM Studio/GGUF:** оставьте `EMBEDDING_ADD_EOS_MANUAL=false` (по умолчанию). llama.cpp добавляет EOS автоматически (см. раздел 5).

---

## 4. Примеры конфигурации .env по профилю ПК

### 4.1 Слабый ПК (8 GB RAM)

```env
# === Путь к конфигурации ===
CONFIG_PATH=C:\path\to\your\1c\config

# === Эмбеддинги (LM Studio или удалённый API) ===
EMBEDDING_API_BASE=http://localhost:1234/v1
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v2-moe
EMBEDDING_DIMENSION=768
EMBEDDING_API_KEY=lm-studio

# === Чанки и контекст (nomic v2: 512 токенов) ===
EMBEDDING_MAX_TOKENS=512
CHUNK_MAX_TOKENS=512
CHUNK_OVERLAP_TOKENS=100

# === Поиск ===
DEFAULT_SEARCH_LIMIT=5
MAX_SEARCH_LIMIT=20
LOG_LEVEL=INFO
```

**Локальная модель (sentence-transformers) вместо API:**

```env
EMBEDDING_API_BASE=
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=384
EMBEDDING_MAX_TOKENS=512
CHUNK_MAX_TOKENS=512
CHUNK_OVERLAP_TOKENS=100
```

---

### 4.2 Средний ПК (16 GB RAM)

```env
CONFIG_PATH=C:\path\to\your\1c\config

# Локальная модель nomic v1.5 (8192 токенов)
EMBEDDING_API_BASE=
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5
EMBEDDING_DIMENSION=768

# Чанки под длинный контекст — целая процедура в одном чанке
EMBEDDING_MAX_TOKENS=1024
CHUNK_MAX_TOKENS=1024
CHUNK_OVERLAP_TOKENS=100

DEFAULT_SEARCH_LIMIT=5
MAX_SEARCH_LIMIT=20
LOG_LEVEL=INFO
```

**Альтернатива (32K контекст):** `Qwen/Qwen3-Embedding-0.6B`, `EMBEDDING_DIMENSION=1024` (при LM Studio/GGUF EOS добавляется автоматически, см. раздел 5)

---

### 4.3 Мощный ПК (32 GB RAM)

```env
CONFIG_PATH=C:\path\to\your\1c\config

# BGE-M3 (8192 токенов, 100+ языков) или Qwen3-Embedding-4B
EMBEDDING_API_BASE=
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIMENSION=1024

# Максимальный контекст — длинные процедуры целиком
EMBEDDING_MAX_TOKENS=2048
CHUNK_MAX_TOKENS=2048
CHUNK_OVERLAP_TOKENS=150

DEFAULT_SEARCH_LIMIT=7
MAX_SEARCH_LIMIT=25
LOG_LEVEL=INFO
```

**Альтернатива:** `Qwen/Qwen3-Embedding-4B`, `EMBEDDING_DIMENSION=2560` (при LM Studio/GGUF EOS добавляется автоматически, см. раздел 5)

---

### 4.4 Максимальная точность (48+ GB RAM или GPU 16+ GB)

```env
CONFIG_PATH=C:\path\to\your\1c\config

# Qwen3-Embedding-8B — лидер MTEB (70.58)
EMBEDDING_API_BASE=
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
EMBEDDING_DIMENSION=4096
# При LM Studio/GGUF: EOS добавляется llama.cpp автоматически, не включайте EMBEDDING_ADD_EOS_MANUAL (см. раздел 5)
# EMBEDDING_ADD_EOS_MANUAL=false

# Максимальный контекст
EMBEDDING_MAX_TOKENS=4096
CHUNK_MAX_TOKENS=4096
CHUNK_OVERLAP_TOKENS=150

DEFAULT_SEARCH_LIMIT=10
MAX_SEARCH_LIMIT=25
LOG_LEVEL=INFO
```

---

## 5. Qwen3 через LM Studio / GGUF: предупреждение EOS

При использовании Qwen3-Embedding (например, `text-embedding-qwen3-embedding-4b`) через LM Studio может появляться предупреждение:

```
[WARNING] At least one last token in strings embedded is not SEP.
'tokenizer.ggml.add_eos_token' should be set to 'true' in the GGUF header
```

### Почему это происходит

Предупреждение означает, что в GGUF-заголовке модели не установлен флаг `tokenizer.ggml.add_eos_token`. Однако **llama.cpp (бэкенд LM Studio) всё равно добавляет EOS-токен автоматически** на уровне BPE-токенизатора — это подтверждается тем, что при ручном добавлении EOS в тексте появляется сообщение:

```
Added a EOS token... So now the final prompt ends with 2 EOS tokens
```

Таким образом, предупреждение **косметическое** и на качество эмбеддингов не влияет.

### Рекомендация: `EMBEDDING_ADD_EOS_MANUAL=false`

Параметр `EMBEDDING_ADD_EOS_MANUAL` должен быть **`false`** (или не задан). Это значение по умолчанию.

```env
# Правильно (по умолчанию):
EMBEDDING_ADD_EOS_MANUAL=false
```

Если установить `true`, `QwenEOSEmbeddingWrapper` добавит `<|endoftext|>` в текст, а llama.cpp добавит второй EOS на уровне токенизатора — получится **двойной EOS**, что может ухудшить качество эмбеддингов.

| Модель | EMBEDDING_ADD_EOS_MANUAL | Примечание |
|--------|--------------------------|------------|
| Qwen3-Embedding-* (LM Studio / GGUF) | `false` (по умолчанию) | llama.cpp добавляет EOS автоматически |
| nomic, BGE-M3, MiniLM | `false` (по умолчанию) | EOS не требуется |

Проверка имени модели выполняется case-insensitive: `Qwen3`, `qwen3`, `QWEN3`, `text-embedding-qwen3-embedding-4b` — все варианты распознаются корректно.

### Если ранее использовали `EMBEDDING_ADD_EOS_MANUAL=true`

1. Установите в `.env` файле профиля:

```env
EMBEDDING_ADD_EOS_MANUAL=false
```

2. **Переиндексируйте с `--clear`** — эмбеддинги с двойным EOS и с одинарным EOS различаются:

```cmd
python index_all.py --profile your_project --clear
```

### Предупреждение о `add_eos_token`

Предупреждение `"add_eos_token should be true"` продолжит отображаться в LM Studio — это нормально. Оно генерируется llama.cpp на основе GGUF-заголовка и не может быть подавлено без пересборки GGUF-файла. На работу системы оно не влияет.

---

## 6. RAG (если планируется)

Параметры для передачи контекста в LLM при использовании RAG:

| Конфигурация ПК | RAG_CONTEXT_LIMIT | RAG_MAX_CONTEXT_CHARS | LLM модель |
|-----------------|-------------------|------------------------|------------|
| Слабый (8 GB) | 3 | 2500–3000 | Qwen2.5-1.5B |
| Средний (16 GB) | 5 | 4000–6000 | Qwen2.5-3B / 7B |
| Мощный (32 GB) | 7–10 | 8000–12000 | Qwen2.5-7B, Llama-3 |
| Макс. точность (48+ GB) | 10 | 12000+ | Qwen2.5-7B, Llama-3 |

---

## 7. Проверка и валидация

### 6.1 После смены модели — переиндексация

При смене модели эмбеддингов или параметров чанков необходимо переиндексировать конфигурацию:

```cmd
run_index_your_project.cmd
```

Или с очисткой:

```cmd
set PROJECT_PROFILE=your_project
python run_indexer.py --clear --vector-only
```

### 6.2 Проверка настроек

При запуске индексатора или сервера в логах отображаются текущие параметры:

- `EMBEDDING_MAX_CHARS` / `EMBEDDING_MAX_TOKENS`
- `CHUNK_MAX_CHARS` / `CHUNK_MAX_TOKENS`
- `CHUNK_OVERLAP_TOKENS`

Убедитесь, что значения соответствуют выбранной модели.

### 7.3 Что сделать после обновления проекта

1. **Установить зависимость:** `pip install rank_bm25`
2. **Переиндексировать** при смене `VECTOR_DISTANCE_METRIC`: `python run_indexer.py --clear --vector-only`
3. **Для гибридного поиска** задать в `.env`: `HYBRID_SEARCH_ALPHA=0.7`

---

## 8. Сводная таблица выбора

| Критерий | Слабый ПК | Средний ПК | Мощный ПК | Макс. точность |
|----------|-----------|------------|-----------|----------------|
| **RAM** | 8 GB | 16 GB | 32 GB | 48+ GB / GPU 16 GB |
| **Embedding** | API или MiniLM | nomic v1.5 | BGE-M3 / Qwen3-4B | Qwen3-8B |
| **Чанк (токены)** | 512 | 1024 | 2048 | 2048–4096 |
| **EMBEDDING_MAX_CHARS** | 1024 | 2048 | 4096 | 4096–8192 |
| **DEFAULT_SEARCH_LIMIT** | 5 | 5–7 | 7 | 10 |

---

## 9. Ссылки

- [README проекта](../README.md) — общая настройка
- [MCP_SETUP.md](MCP_SETUP.md) — подключение к Cursor
- ИТС 1С: Оформление модулей — стандарты структуры кода BSL
