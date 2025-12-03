# Конкретные улучшения кода для Docker MCP Orchestrator

## 🎯 Приоритет 1: Автоматическая активация context7

### Изменения в server.py

```python
# Добавить после MCP_SERVER_REGISTRY (строка ~121)

# Серверы которые требуют документации через context7
LIBRARY_SERVERS_REQUIRING_DOCS = {
    "redis", "postgres", "playwright", "github", 
    "fetch", "desktop-commander"
}

# Конфигурация зависимостей серверов
SERVER_DEPENDENCIES = {
    "redis": {
        "documentation": ["context7"],
        "reason": "Redis API documentation and examples"
    },
    "postgres": {
        "documentation": ["context7"],
        "reason": "PostgreSQL query syntax and API"
    },
    "playwright": {
        "documentation": ["context7"],
        "reason": "Playwright API and browser automation docs"
    },
    "github": {
        "documentation": ["context7"],
        "reason": "GitHub API documentation"
    },
    "fetch": {
        "documentation": ["context7"],
        "reason": "HTTP client library documentation"
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

### Обновить activate_server (строка ~335)

```python
@mcp.tool()
async def activate_server(
    server_name: str, 
    reason: str = "",
    auto_activate_deps: bool = True  # НОВЫЙ ПАРАМЕТР
) -> str:
    """
    Activate (enable) an MCP server in Docker MCP Toolkit.
    
    **CRITICAL AI INSTRUCTIONS:**
    
    When user asks to work with ANY library, framework, or technology:
    
    1. **ALWAYS activate the library server first:**
       - Redis → activate_server("redis")
       - PostgreSQL → activate_server("postgres")
       - Playwright → activate_server("playwright")
    
    2. **Documentation is automatically activated:**
       - If auto_activate_deps=True (default), context7 is auto-activated
       - For libraries: redis, postgres, playwright, github, etc.
       - You can disable with auto_activate_deps=False
    
    3. **Use context7 to get documentation:**
       - resolve-library-id("library_name") to find library ID
       - get-library-docs(library_id, query="...") to get docs
    
    4. **Then use library tools:**
       - After getting docs, use library-specific tools
    
    **Example workflow:**
    ```
    User: "Set up Redis cache"
    
    Step 1: activate_server("redis", "User needs Redis operations")
            → Automatically activates context7 for documentation
    
    Step 2: Use context7 tools:
            - resolve-library-id("redis")
            - get-library-docs(redis_id, query="cache setup")
    
    Step 3: Use Redis tools:
            - redis set session:user123 "data"
            - redis config set maxmemory 256mb
    ```
    
    Args:
        server_name: Server to activate (e.g., "playwright", "github", "redis")
        reason: Brief explanation why this server is needed
        auto_activate_deps: Automatically activate dependencies (default: True)
    
    Returns:
        Status message with available tools
    
    Examples:
        activate_server("playwright", "Need to screenshot a website")
        activate_server("github", "Creating an issue")
        activate_server("redis", "Setting up cache", auto_activate_deps=True)
    """
    # Validate
    if server_name not in MCP_SERVER_REGISTRY:
        available = ", ".join(sorted(MCP_SERVER_REGISTRY.keys()))
        return f"❌ Unknown server: '{server_name}'\n\nAvailable: {available}"
    
    if server_name in state.active_servers:
        config = MCP_SERVER_REGISTRY[server_name]
        return (f"ℹ️ Server '{server_name}' is already active.\n\n"
                f"**Tools**: {config.tools_summary}")
    
    config = MCP_SERVER_REGISTRY[server_name]
    logger.info(f"Activating: {server_name} (reason: {reason})")
    
    success, output = enable_server(server_name)
    
    if success:
        state.active_servers.add(server_name)
        tools = get_server_tools(server_name)
        state.server_tools_cache[server_name] = tools
        
        lines = [
            f"✅ **{server_name}** activated!",
            f"",
            f"**Description**: {config.description}",
        ]
        
        if tools:
            lines.append(f"\n**Available tools ({len(tools)})**:")
            for t in tools[:12]:
                desc = t.get('description', '')[:60]
                lines.append(f"- `{t.get('name')}`: {desc}")
            if len(tools) > 12:
                lines.append(f"- _...and {len(tools) - 12} more_")
        
        # НОВОЕ: Автоматическая активация зависимостей
        activated_deps = []
        if auto_activate_deps:
            dependencies = get_required_dependencies(server_name)
            for dep_server, dep_reason in dependencies:
                if dep_server not in state.active_servers:
                    logger.info(f"Auto-activating dependency: {dep_server} for {server_name}")
                    dep_success, dep_output = enable_server(dep_server)
                    if dep_success:
                        state.active_servers.add(dep_server)
                        dep_tools = get_server_tools(dep_server)
                        state.server_tools_cache[dep_server] = dep_tools
                        activated_deps.append((dep_server, dep_reason))
                    else:
                        logger.warning(f"Failed to auto-activate {dep_server}: {dep_output}")
        
        if activated_deps:
            lines.append(f"\n📚 **Dependencies auto-activated:**")
            for dep_server, dep_reason in activated_deps:
                lines.append(f"  - **{dep_server}**: {dep_reason}")
                if dep_server == "context7":
                    lines.append(f"    → Use `resolve-library-id(\"{server_name}\")` to get docs")
                    lines.append(f"    → Use `get-library-docs(library_id, query=\"...\")` for details")
        
        if config.requires_auth:
            lines.append(f"\n⚠️ Requires {config.auth_type} auth. "
                        "Configure in Docker MCP Toolkit.")
        
        lines.append(f"\n📌 Tools from '{server_name}' are now available "
                    "via MCP gateway.")
        
        return "\n".join(lines)
    else:
        state.last_error = output
        return f"❌ Failed to activate '{server_name}': {output}"
```

---

## 🎯 Приоритет 2: Новый инструмент setup_library_environment

### Добавить после activate_server (после строки ~398)

```python
@mcp.tool()
async def setup_library_environment(
    library_name: str, 
    task_description: str = ""
) -> str:
    """
    Smart setup for working with a library/framework.
    
    Automatically activates:
    1. The library server (redis, postgres, playwright, etc.)
    2. Context7 server for documentation
    
    **When to use:**
    - User asks to work with any library/framework
    - You need both the library tools AND documentation
    - This is the RECOMMENDED way to start working with libraries
    
    **AI Instructions:**
    When user mentions a library (Redis, PostgreSQL, Playwright, etc.):
    1. Use this tool instead of activate_server() directly
    2. It handles both library and documentation setup
    3. Then use context7 tools to get documentation
    4. Finally use library tools for actual work
    
    Args:
        library_name: Name of library (redis, postgres, playwright, github, etc.)
        task_description: What you need to do (optional, for better context)
    
    Returns:
        Setup instructions and next steps
    
    Examples:
        setup_library_environment("redis", "cache setup")
        setup_library_environment("postgres", "database queries")
        setup_library_environment("playwright", "browser automation")
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
            f"**Available libraries**: {available}\n\n"
            f"**Alternative**: Use `activate_server()` directly with server name."
        )
    
    results = []
    activated_servers = []
    
    # 1. Активируем основной сервер
    if server_name not in state.active_servers:
        logger.info(f"Activating {server_name} for library {library_name}")
        success, output = enable_server(server_name)
        if success:
            state.active_servers.add(server_name)
            tools = get_server_tools(server_name)
            state.server_tools_cache[server_name] = tools
            results.append(f"✅ **{server_name}** activated")
            activated_servers.append(server_name)
        else:
            return f"❌ Failed to activate {server_name}: {output}"
    else:
        results.append(f"ℹ️ **{server_name}** already active")
    
    # 2. Активируем context7 для документации
    if "context7" not in state.active_servers:
        logger.info(f"Activating context7 for {library_name} documentation")
        success, output = enable_server("context7")
        if success:
            state.active_servers.add("context7")
            tools = get_server_tools("context7")
            state.server_tools_cache["context7"] = tools
            results.append("✅ **context7** activated for documentation")
            activated_servers.append("context7")
        else:
            results.append(f"⚠️ Failed to activate context7: {output}")
            logger.warning(f"Context7 activation failed: {output}")
    else:
        results.append("ℹ️ **context7** already active")
    
    # 3. Формируем инструкции
    config = MCP_SERVER_REGISTRY.get(server_name)
    
    instructions = [
        "# 🚀 Library Environment Ready",
        "",
        *results,
    ]
    
    if activated_servers:
        instructions.append(f"\n**Activated servers**: {', '.join(activated_servers)}")
    
    instructions.extend([
        "",
        f"## 📚 Next Steps for {library_name}:",
        "",
        "### 1. Get Documentation:",
        f"Use context7 tools to get {library_name} documentation:",
        f"  - `resolve-library-id(\"{library_name}\")` → Get library ID",
        f"  - `get-library-docs(library_id, query=\"your question\")` → Get docs",
        "",
        "**Example:**",
        f"```",
        f"library_id = resolve-library-id(\"{library_name}\")",
        f"docs = get-library-docs(library_id, query=\"{task_description or 'API reference'}\")",
        f"```",
        "",
        "### 2. Use Library Tools:",
        f"After getting docs, use {server_name} tools:",
    ])
    
    # Показываем примеры инструментов
    if server_name in state.server_tools_cache:
        tools = state.server_tools_cache[server_name]
        for tool in tools[:5]:
            tool_name = tool.get('name', '?')
            tool_desc = tool.get('description', '')[:50]
            instructions.append(f"  - `{tool_name}`: {tool_desc}")
        if len(tools) > 5:
            instructions.append(f"  - _...and {len(tools) - 5} more_")
    
    instructions.extend([
        "",
        "### 3. Check Available Tools:",
        "Use `get_active_servers()` to see all available tools from active servers.",
        "",
        "---",
        f"**Tip**: Documentation is essential for correct API usage. "
        f"Always get docs before using {library_name} tools."
    ])
    
    return "\n".join(instructions)
```

---

## 🎯 Приоритет 3: Улучшить activate_for_task

### Обновить activate_for_task (строка ~427)

```python
@mcp.tool()
async def activate_for_task(task_description: str) -> str:
    """
    Automatically recommend and activate servers for a task.
    
    **IMPROVED:** Now automatically includes context7 for documentation
    when working with libraries.
    
    **AI Instructions:**
    Use this when:
    - Task description mentions libraries/frameworks
    - You're not sure which servers are needed
    - You want automatic server selection
    
    The tool will:
    1. Analyze task keywords
    2. Recommend appropriate servers
    3. Auto-include context7 if libraries are detected
    4. Activate all recommended servers
    
    Args:
        task_description: What you want to accomplish
    
    Returns:
        Recommendations and activation results
    
    Examples:
        activate_for_task("scrape website and create GitHub issue")
        activate_for_task("query PostgreSQL database")
        activate_for_task("set up Redis cache")
    """
    task_lower = task_description.lower()
    recommendations: list[tuple[str, str]] = []
    
    # Keyword-based matching
    keyword_map = {
        "context7": ["documentation", "docs", "api reference", "library", 
                     "framework", "package", "sdk"],
        "playwright": ["browser", "screenshot", "scrape", "website", "click", 
                       "form", "web page", "navigate", "automation"],
        "github": ["github", "repository", "repo", "issue", "pull request", 
                   "pr", "commit", "code search", "gist"],
        "fetch": ["http", "api", "fetch", "download", "request", "url", "curl"],
        "desktop-commander": ["file", "folder", "directory", "command", 
                              "execute", "process", "terminal", "shell"],
        "postgres": ["database", "sql", "query", "postgres", "postgresql", 
                     "table", "db"],
        "redis": ["cache", "redis", "session", "pub/sub", "key-value"],
        "sequential-thinking": ["analyze", "think", "reason", "plan", 
                                "complex", "multi-step", "decision"],
    }
    
    for server, keywords in keyword_map.items():
        for kw in keywords:
            if kw in task_lower:
                config = MCP_SERVER_REGISTRY[server]
                recommendations.append((server, f"Keyword '{kw}': {config.description}"))
                break
    
    # НОВОЕ: Автоматически добавляем context7 для библиотек
    library_keywords = [
        "redis", "postgres", "database", "library", "framework",
        "api", "sdk", "documentation", "docs", "package", "cache"
    ]
    
    needs_documentation = any(
        kw in task_lower for kw in library_keywords
    )
    
    # Проверяем что есть хотя бы одна библиотека в рекомендациях
    library_servers = {"redis", "postgres", "playwright", "github", "fetch"}
    has_library = any(
        server in library_servers 
        for server, _ in recommendations
    )
    
    # Добавляем context7 если работаем с библиотеками
    if (needs_documentation or has_library) and "context7" not in [s for s, _ in recommendations]:
        recommendations.append((
            "context7",
            "Auto-added: Documentation server for library APIs and examples"
        ))
    
    if not recommendations:
        return ("🤔 No servers auto-detected for this task.\n\n"
                "Use `list_available_servers()` to see options, or be more "
                "specific (e.g., 'browser', 'github', 'database').")
    
    result = [f"# 🔍 Task: {task_description[:80]}{'...' if len(task_description) > 80 else ''}\n"]
    result.append("## Recommended Servers:\n")
    
    activated = []
    for server, reason in recommendations:
        if server in state.active_servers:
            result.append(f"- **{server}**: Already active ✅")
        else:
            success, _ = enable_server(server)
            if success:
                state.active_servers.add(server)
                tools = get_server_tools(server)
                state.server_tools_cache[server] = tools
                activated.append(server)
                result.append(f"- **{server}**: Activated ✅")
            else:
                result.append(f"- **{server}**: Failed ❌")
        result.append(f"  _{reason}_")
    
    if activated:
        result.append(f"\n📌 **Activated**: {', '.join(activated)}")
        result.append("Tools are now available via MCP gateway.")
        
        # Добавляем подсказку про документацию
        if "context7" in activated:
            library_activated = [s for s in activated if s in library_servers]
            if library_activated:
                result.append(f"\n📚 **Documentation ready**:")
                result.append(f"Use context7 tools to get docs for: {', '.join(library_activated)}")
                result.append(f"  - `resolve-library-id(\"library_name\")`")
                result.append(f"  - `get-library-docs(library_id, query=\"...\")`")
    
    return "\n".join(result)
```

---

## 🎯 Приоритет 4: Автоматическая деактивация по таймауту

### Добавить в начало файла (после импортов)

```python
from datetime import datetime, timedelta
```

### Добавить после OrchestratorState (строка ~136)

```python
@dataclass
class ServerUsage:
    """Отслеживание использования сервера"""
    last_used: datetime
    access_count: int = 0

# Глобальное состояние использования
server_usage: dict[str, ServerUsage] = {}
```

### Добавить функцию обновления использования

```python
def update_server_usage(server_name: str):
    """Обновляет метрики использования сервера"""
    now = datetime.now()
    if server_name in server_usage:
        server_usage[server_name].last_used = now
        server_usage[server_name].access_count += 1
    else:
        server_usage[server_name] = ServerUsage(
            last_used=now,
            access_count=1
        )
```

### Добавить фоновую задачу очистки

```python
async def background_cleanup_task():
    """
    Фоновая задача для автоматической деактивации неиспользуемых серверов.
    Деактивирует серверы неиспользуемые более 10 минут.
    """
    while True:
        await asyncio.sleep(60)  # Проверяем каждую минуту
        
        now = datetime.now()
        timeout = timedelta(minutes=10)
        to_deactivate = []
        
        for server in list(state.active_servers):
            usage = server_usage.get(server)
            if usage:
                if (now - usage.last_used) > timeout:
                    to_deactivate.append(server)
            else:
                # Если нет данных об использовании, считаем старым
                # (сервер был активирован до добавления трекинга)
                to_deactivate.append(server)
        
        for server in to_deactivate:
            logger.info(f"Auto-deactivating {server} (inactive >10min)")
            success, _ = disable_server(server)
            if success:
                state.active_servers.discard(server)
                state.server_tools_cache.pop(server, None)
                server_usage.pop(server, None)
```

### Обновить main() для запуска фоновой задачи

```python
def main():
    """Main entry point"""
    logger.info("Starting Docker MCP Orchestrator...")
    
    # Initial sync
    enabled = get_enabled_servers()
    state.active_servers = set(enabled) & set(MCP_SERVER_REGISTRY.keys())
    
    if state.active_servers:
        logger.info(f"Found active: {state.active_servers}")
        for server in state.active_servers:
            state.server_tools_cache[server] = get_server_tools(server)
            # Инициализируем использование
            update_server_usage(server)
    
    # Запускаем фоновую задачу очистки
    # ВНИМАНИЕ: FastMCP может не поддерживать фоновые задачи напрямую
    # Возможно потребуется использовать asyncio.create_task() в другом месте
    # или реализовать через периодические вызовы
    
    logger.info("Ready!")
    mcp.run()
```

**Примечание:** FastMCP может не поддерживать фоновые задачи напрямую. Альтернатива - добавить инструмент `cleanup_unused_servers()` который можно вызывать периодически.

---

## 🎯 Приоритет 5: Инструмент для очистки неиспользуемых серверов

### Добавить после deactivate_all (после строки ~503)

```python
@mcp.tool()
async def cleanup_unused_servers(max_idle_minutes: int = 10) -> str:
    """
    Deactivate servers that haven't been used recently.
    
    Useful for freeing resources and reducing token usage.
    Can be called periodically or when user asks to clean up.
    
    Args:
        max_idle_minutes: Deactivate servers idle longer than this (default: 10)
    
    Returns:
        Cleanup results
    """
    now = datetime.now()
    timeout = timedelta(minutes=max_idle_minutes)
    to_deactivate = []
    
    for server in list(state.active_servers):
        usage = server_usage.get(server)
        if usage:
            idle_time = now - usage.last_used
            if idle_time > timeout:
                to_deactivate.append((server, idle_time))
        else:
            # Сервер без данных использования
            to_deactivate.append((server, None))
    
    if not to_deactivate:
        return f"ℹ️ No servers to deactivate (all used within last {max_idle_minutes} minutes)."
    
    results = []
    for server, idle_time in to_deactivate:
        success, output = disable_server(server)
        if success:
            state.active_servers.discard(server)
            state.server_tools_cache.pop(server, None)
            server_usage.pop(server, None)
            
            if idle_time:
                idle_str = f"{int(idle_time.total_seconds() / 60)} minutes"
            else:
                idle_str = "unknown"
            
            results.append(f"✅ {server} (idle: {idle_str})")
        else:
            results.append(f"❌ {server}: {output}")
    
    return "# 🧹 Cleanup Results\n\n" + "\n".join(results)
```

---

## 📝 Резюме изменений

### Файлы для изменения:

1. **src/mcp_orchestrator/server.py**
   - Добавить константы зависимостей (после MCP_SERVER_REGISTRY)
   - Добавить функцию get_required_dependencies()
   - Обновить activate_server() с авто-активацией зависимостей
   - Добавить setup_library_environment()
   - Улучшить activate_for_task() с авто-добавлением context7
   - Добавить cleanup_unused_servers()
   - Добавить трекинг использования серверов

### Порядок внедрения:

1. **Шаг 1:** Добавить константы и функции зависимостей
2. **Шаг 2:** Обновить activate_server() с авто-активацией
3. **Шаг 3:** Добавить setup_library_environment()
4. **Шаг 4:** Улучшить activate_for_task()
5. **Шаг 5:** Добавить cleanup_unused_servers()

### Тестирование:

После каждого шага:
- Запустить тесты: `pytest tests/`
- Проверить работу через MCP клиент
- Убедиться что context7 активируется автоматически
