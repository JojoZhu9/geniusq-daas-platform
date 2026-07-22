from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_delivery_plan_documents_current_demo_capabilities():
    proposal = read_text("docs/智能问数优化实施计划书.md")

    for section in [
        "项目背景",
        "建设目标",
        "当前已实现功能",
        "技术架构",
        "核心运行逻辑",
        "数据与安全设计",
        "测试与验收",
        "后续扩展建议",
    ]:
        assert section in proposal

    for capability in [
        "智能问数工作台",
        "数据源管理",
        "知识库管理",
        "DeepSeek Text-to-SQL",
        "仪表盘",
        "历史会话",
        "SQLite",
    ]:
        assert capability in proposal


def test_readme_documents_local_run_deepseek_and_cloud_deployment():
    readme = read_text("README.md")

    for expected in [
        "start-demo.ps1",
        "LLM_MODE=offline",
        "LLM_MODE=deepseek",
        "DEEPSEEK_API_KEY",
        "127.0.0.1:5173",
        "pytest",
        "npm --prefix frontend run test:run",
        "Vercel + Render",
        "VITE_API_BASE_URL",
        "CORS_ORIGINS",
        "onrender.com",
    ]:
        assert expected in readme


def test_environment_example_keeps_offline_as_the_default_and_documents_cors():
    environment = read_text(".env.example")

    for expected in [
        "LLM_MODE=offline",
        "QUERY_ROW_LIMIT=500",
        "LLM_API_KEY=",
        "CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173",
    ]:
        assert expected in environment


def test_launcher_is_safe_for_windows_powershell_51_encoding():
    launcher = read_text("start-demo.ps1")
    assert launcher.isascii(), (
        "Windows PowerShell 5.1 reads UTF-8 scripts without a BOM as the local "
        "ANSI code page; keep the launcher ASCII-only so powershell -File parses it."
    )
