# Как AI понимает работу с Redis → Context7 через Docker MCP Orchestrator

## 🎯 Проблема: AI не знает о необходимости документации

### Сценарий проблемы

```
Пользователь: "Настрой Redis кэш для хранения сессий"

Текущее поведение AI:
1. AI видит инструмент activate_server("redis")
2. AI активирует Redis сервер
3. AI пытается использовать Redis инструменты
4. ❌ AI НЕ ЗНАЕТ что нужно активировать context7 для документации
5. ❌ AI работает вслепую без понимания Redis API
```

### Почему это происходит?

1. **AI не видит связи** между "работа с Redis" и "нужна документация"
2. **Нет явных инструкций** в описаниях инструментов
3. **Нет автоматической активации зависимостей**
4. **AI должна сама догадаться** использовать context7

---

## ✅ Решение: Многоуровневая система

### Уровень 1: Явные инструкции в docstrings

**Текущий код:**
```python
@mcp.tool()
async def activate_server(server_name: str, reason: str = "") -> str:
    """
    Activate (enable) an MCP server in Docker MCP Toolkit.
    ...
    """
```

**Улучшенный код:**
```python
@mcp.tool()
async def activate_server(server_name: str, reason: str = "") -> str:
    """
    Activate (enable) an MCP server in Docker MCP Toolkit.
    
    **CRITICAL AI INSTRUCTIONS:**
    
    When user asks to work with ANY library, framework, or technology:
    
    1. **ALWAYS activate the library server first:**
       - Redis → activate_server("redis")
       - PostgreSQL → activate_server("postgres")
       - Playwright → activate_server("playwright")
    
    2. **ALWAYS activate context7 for documentation:**
       - After activating library server, activate context7
       - Example: activate_server("redis") → activate_server("context7")
       - Context7 provides up-to-date library documentation
    
    3. **Use context7 to get documentation:**
       - resolve-library-id("redis") to find library ID
       - get-library-docs(library_id, query="...") to get docs
    
    4. **Then use library tools:**
       - After getting docs, use library-specific tools
    
    **Example workflow:**
    ```
    User: "Set up Redis cache"
    
    Step 1: activate_server("redis", "User needs Redis operations")
    Step 2: activate_server("context7", "Need Redis documentation")
    Step 3: Use context7 tools:
            - resolve-library-id("redis")
            - get-library-docs(redis_id, query="cache setup")
    Step 4: Use Redis tools:
            - redis set session:user123 "data"
            - redis config set maxmemory 256mb
    ```
    
    Args:
        server_name: Server to activate
        reason: Why this server is needed
    """
```

### Уровень 2: Автоматическая активация зависимостей

**Добавить в server.py:**

```python
# Маппинг серверов которые требуют документации
LIBRARY_SERVERS_REQUIRING_DOCS = {
    "redis", "postgres", "playwright", "github", 
    "fetch", "desktop-commander"
}

@mcp.tool()
async def activate_server(
    server_name: str, 
    reason: str = "",
    auto_activate_docs: bool = True  # НОВЫЙ ПАРАМЕТР
) -> str:
    """
    Activate server with automatic documentation server activation.
    """
    # ... существующий код валидации ...
    
    # Активируем основной сервер
    success, output = enable_server(server_name)
    
    if success:
        state.active_servers.add(server_name)
        tools = get_server_tools(server_name)
        state.server_tools_cache[server_name] = tools
        
        result_lines = [
            f"✅ **{server_name}** activated!",
            f"**Description**: {config.description}",
        ]
        
        # АВТОМАТИЧЕСКАЯ АКТИВАЦИЯ CONTEXT7
        if (auto_activate_docs and 
            server_name in LIBRARY_SERVERS_REQUIRING_DOCS and
            "context7" not in state.active_servers):
            
            # Активируем context7 автоматически
            docs_success, _ = enable_server("context7")
            if docs_success:
                state.active_servers.add("context7")
                docs_tools = get_server_tools("context7")
                state.server_tools_cache["context7"] = docs_tools
                
                result_lines.append(
                    "\n📚 **Context7 automatically activated for documentation!**"
                )
                result_lines.append(
                    "Use context7 tools to get library documentation:"
                )
                result_lines.append(
                    f"  - resolve-library-id(\"{server_name}\")"
                )
                result_lines.append(
                    "  - get-library-docs(library_id, query=\"...\")"
                )
        
        # ... остальной код ...
        
        return "\n".join(result_lines)
```

### Уровень 3: Специальный инструмент для библиотек

**Новый инструмент:**

```python
@mcp.tool()
async def setup_library_environment(
    library_name: str, 
    task_description: str = ""
) -> str:
    """
    Smart setup for working with a library/framework.
    
    Automatically activates:
    1. The library server (redis, postgres, etc.)
    2. Context7 server for documentation
    
    **When to use:**
    - User asks to work with any library/framework
    - You need both the library tools AND documentation
    - Example: "setup redis cache" → use this tool
    
    Args:
        library_name: Name of library (redis, postgres, playwright, etc.)
        task_description: What you need to do (optional, for context)
    
    Returns:
        Setup instructions and next steps
    
    Examples:
        setup_library_environment("redis", "cache setup")
        setup_library_environment("postgres", "database queries")
    """
    # Маппинг библиотек на серверы
    LIBRARY_TO_SERVER = {
        "redis": "redis",
        "postgres": "postgres",
        "postgresql": "postgres",
        "playwright": "playwright",
        "github": "github",
        "fetch": "fetch",
    }
    
    server_name = LIBRARY_TO_SERVER.get(library_name.lower())
    if not server_name:
        available = ", ".join(LIBRARY_TO_SERVER.keys())
        return (
            f"❌ Unknown library: '{library_name}'\n\n"
            f"Available: {available}\n\n"
            f"Or use activate_server() directly."
        )
    
    results = []
    
    # 1. Активируем основной сервер
    if server_name not in state.active_servers:
        success, output = enable_server(server_name)
        if success:
            state.active_servers.add(server_name)
            tools = get_server_tools(server_name)
            state.server_tools_cache[server_name] = tools
            results.append(f"✅ **{server_name}** activated")
        else:
            return f"❌ Failed to activate {server_name}: {output}"
    else:
        results.append(f"ℹ️ **{server_name}** already active")
    
    # 2. Активируем context7 для документации
    if "context7" not in state.active_servers:
        success, output = enable_server("context7")
        if success:
            state.active_servers.add("context7")
            tools = get_server_tools("context7")
            state.server_tools_cache["context7"] = tools
            results.append("✅ **context7** activated for documentation")
        else:
            results.append(f"⚠️ Failed to activate context7: {output}")
    else:
        results.append("ℹ️ **context7** already active")
    
    # 3. Формируем инструкции
    config = MCP_SERVER_REGISTRY.get(server_name)
    
    instructions = [
        "# 🚀 Library Environment Ready",
        "",
        *results,
        "",
        f"## 📚 Next Steps for {library_name}:",
        "",
        "### 1. Get Documentation:",
        f"Use context7 tools to get {library_name} documentation:",
        f"  - `resolve-library-id(\"{library_name}\")`",
        f"  - `get-library-docs(library_id, query=\"your question\")`",
        "",
        "### 2. Use Library Tools:",
        f"After getting docs, use {server_name} tools:",
    ]
    
    # Показываем примеры инструментов
    if server_name in state.server_tools_cache:
        tools = state.server_tools_cache[server_name]
        for tool in tools[:5]:
            tool_name = tool.get('name', '?')
            instructions.append(f"  - `{tool_name}`")
        if len(tools) > 5:
            instructions.append(f"  - _...and {len(tools) - 5} more_")
    
    instructions.append("")
    instructions.append("### 3. Check Available Tools:")
    instructions.append("Use `get_active_servers()` to see all available tools.")
    
    return "\n".join(instructions)
```

### Уровень 4: Улучшенный activate_for_task

**Улучшение существующего инструмента:**

```python
@mcp.tool()
async def activate_for_task(task_description: str) -> str:
    """
    Automatically recommend and activate servers for a task.
    
    **IMPROVED:** Now automatically includes context7 for documentation
    when working with libraries.
    """
    task_lower = task_description.lower()
    recommendations: list[tuple[str, str]] = []
    
    # ... существующая логика keyword matching ...
    
    # НОВОЕ: Проверяем нужна ли документация
    library_keywords = [
        "redis", "postgres", "database", "library", "framework",
        "api", "sdk", "documentation", "docs", "package"
    ]
    
    needs_documentation = any(
        kw in task_lower for kw in library_keywords
    )
    
    # Если работаем с библиотеками, добавляем context7
    if needs_documentation and "context7" not in recommendations:
        # Проверяем что есть хотя бы одна библиотека в рекомендациях
        library_servers = {"redis", "postgres", "playwright", "github"}
        has_library = any(
            server in library_servers 
            for server, _ in recommendations
        )
        
        if has_library or any(kw in task_lower for kw in ["library", "framework", "api"]):
            recommendations.append((
                "context7",
                "Auto-added: Documentation server for library APIs"
            ))
    
    # ... остальной код активации ...
```

---

## 🔄 Полный Workflow для AI

### Сценарий: "Настрой Redis кэш"

#### Вариант 1: Использование setup_library_environment (рекомендуется)

```
1. Пользователь: "Настрой Redis кэш для сессий"

2. AI анализирует:
   - Нужен Redis
   - Нужна документация по Redis
   - Использует setup_library_environment("redis", "cache setup")

3. Оркестратор:
   ✅ Активирует redis сервер
   ✅ Активирует context7 сервер
   ✅ Возвращает инструкции

4. AI получает ответ:
   ✅ redis activated
   ✅ context7 activated for documentation
   
   Next steps:
   1. Get Documentation:
      - resolve-library-id("redis")
      - get-library-docs(redis_id, query="cache setup")
   2. Use Redis Tools:
      - redis set ...
      - redis config ...

5. AI выполняет:
   a) resolve-library-id("redis") → получает library_id
   b) get-library-docs(redis_id, query="cache setup for sessions")
   c) Читает документацию
   d) Использует redis инструменты:
      - redis config set maxmemory 256mb
      - redis set session:user123 "data"
```

#### Вариант 2: Использование activate_for_task

```
1. Пользователь: "Настрой Redis кэш"

2. AI использует: activate_for_task("настроить redis кэш")

3. Оркестратор:
   - Находит "redis" по ключевому слову
   - Находит "context7" автоматически (т.к. есть "redis")
   - Активирует оба сервера

4. AI получает:
   ✅ redis activated
   ✅ context7 activated (auto-added for documentation)

5. AI продолжает как в варианте 1
```

#### Вариант 3: Ручная активация (если AI знает про зависимости)

```
1. Пользователь: "Настрой Redis кэш"

2. AI читает docstring activate_server:
   "ALWAYS activate context7 for documentation"

3. AI выполняет:
   - activate_server("redis", "User needs Redis")
   - activate_server("context7", "Need Redis documentation")

4. AI продолжает работу
```

---

## 📋 Чеклист для AI при работе с библиотеками

### Когда пользователь просит работать с библиотекой:

1. ✅ **Определить библиотеку**
   - Redis, PostgreSQL, Playwright, GitHub, etc.

2. ✅ **Выбрать метод активации:**
   - **Лучше:** `setup_library_environment(library_name)`
   - **Альтернатива:** `activate_for_task("task description")`
   - **Ручной:** `activate_server()` дважды (библиотека + context7)

3. ✅ **Получить документацию:**
   - `resolve-library-id("library_name")`
   - `get-library-docs(library_id, query="...")`

4. ✅ **Использовать инструменты библиотеки:**
   - После получения документации
   - Использовать инструменты активированного сервера

5. ✅ **Проверить доступные инструменты:**
   - `get_active_servers()` если нужно

---

## 🎓 Обучение AI через примеры в docstrings

### Пример улучшенного docstring для activate_server:

```python
"""
**AI LEARNING EXAMPLES:**

Example 1: Redis Cache Setup
─────────────────────────────
User: "Set up Redis cache"

AI should:
1. setup_library_environment("redis", "cache setup")
   OR
2. activate_server("redis", "cache setup")
   activate_server("context7", "Redis documentation")
3. resolve-library-id("redis")
4. get-library-docs(redis_id, query="cache configuration")
5. Use redis tools: redis config set, redis set, etc.

Example 2: PostgreSQL Queries
─────────────────────────────
User: "Query PostgreSQL database"

AI should:
1. setup_library_environment("postgres", "database queries")
2. resolve-library-id("postgres")
3. get-library-docs(postgres_id, query="query syntax")
4. Use postgres tools: query(sql="SELECT ...")

Example 3: Browser Automation
──────────────────────────────
User: "Take screenshot of website"

AI should:
1. setup_library_environment("playwright", "browser automation")
2. resolve-library-id("playwright")
3. get-library-docs(playwright_id, query="screenshot")
4. Use playwright tools: browser_navigate, browser_screenshot
"""
```

---

## 🔧 Техническая реализация зависимостей

### Добавить в server.py:

```python
# Конфигурация зависимостей серверов
SERVER_DEPENDENCIES = {
    "redis": {
        "documentation": ["context7"],
        "reason": "Redis API documentation"
    },
    "postgres": {
        "documentation": ["context7"],
        "reason": "PostgreSQL query syntax and API"
    },
    "playwright": {
        "documentation": ["context7"],
        "reason": "Playwright API and examples"
    },
    "github": {
        "documentation": ["context7"],
        "reason": "GitHub API documentation"
    },
}

def get_required_dependencies(server_name: str) -> list[tuple[str, str]]:
    """
    Возвращает список зависимостей для сервера.
    
    Returns:
        List of (dependency_server, reason) tuples
    """
    deps = SERVER_DEPENDENCIES.get(server_name, {})
    docs_deps = deps.get("documentation", [])
    
    return [
        (dep, deps.get("reason", "Required dependency"))
        for dep in docs_deps
    ]
```

### Использование в activate_server:

```python
async def activate_server(server_name: str, reason: str = "",
                         auto_activate_deps: bool = True) -> str:
    # ... активация основного сервера ...
    
    if auto_activate_deps:
        dependencies = get_required_dependencies(server_name)
        for dep_server, dep_reason in dependencies:
            if dep_server not in state.active_servers:
                # Рекурсивно активируем зависимость (без deps чтобы избежать циклов)
                await activate_server(
                    dep_server, 
                    f"{dep_reason} (auto for {server_name})",
                    auto_activate_deps=False
                )
```

---

## 📊 Сравнение подходов

| Подход | Автоматизация | Понятность для AI | Гибкость |
|--------|---------------|-------------------|----------|
| **Текущий** | ❌ Нет | ⚠️ Низкая | ✅ Высокая |
| **Улучшенные docstrings** | ⚠️ Частичная | ✅ Высокая | ✅ Высокая |
| **Авто-активация deps** | ✅ Полная | ✅ Высокая | ⚠️ Средняя |
| **setup_library_environment** | ✅ Полная | ✅ Очень высокая | ⚠️ Средняя |

**Рекомендация:** Комбинация всех подходов:
1. Автоматическая активация зависимостей (прозрачно)
2. Улучшенные docstrings (обучение AI)
3. Специальный инструмент setup_library_environment (удобство)
