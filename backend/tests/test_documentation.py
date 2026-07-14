from pathlib import Path

from app.seed import REQUIREMENT_MAPPINGS


ROOT = Path(__file__).resolve().parents[2]
REQUIREMENT_IDS = {row[0] for row in REQUIREMENT_MAPPINGS}
REQUIRED_SECTIONS = {
    "项目背景",
    "现状问题",
    "建设目标",
    "需求范围",
    "总体方案",
    "功能方案",
    "技术架构",
    "数据与安全",
    "实施阶段与排期",
    "人员分工建议",
    "风险与应对",
    "验收方案",
    "需求追踪矩阵",
}


def test_proposal_and_matrix_cover_every_requirement():
    proposal = (ROOT / "docs" / "智能问数优化实施计划书.md").read_text(
        encoding="utf-8"
    )
    matrix = (ROOT / "docs" / "需求追踪矩阵.md").read_text(encoding="utf-8")
    for requirement_id in REQUIREMENT_IDS:
        assert requirement_id in proposal
        assert requirement_id in matrix
    for section in REQUIRED_SECTIONS:
        assert section in proposal
    assert "四周" in proposal
    assert "本地 Demo 已完成" in proposal
    assert "真实平台集成建议" in proposal


def test_readme_documents_offline_start_and_optional_llm():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "start-demo.ps1" in readme
    assert "LLM_MODE=offline" in readme
    assert "LLM_MODE=openai-compatible" in readme
    assert "127.0.0.1:5173" in readme
    assert "pytest" in readme
    assert "npm.cmd run test:run" in readme


def test_environment_example_keeps_offline_as_the_default():
    environment = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "LLM_MODE=offline" in environment
    assert "QUERY_ROW_LIMIT=500" in environment
    assert "LLM_API_KEY=" in environment


def test_launcher_is_safe_for_windows_powershell_51_encoding():
    launcher = (ROOT / "start-demo.ps1").read_text(encoding="utf-8")
    assert launcher.isascii(), (
        "Windows PowerShell 5.1 reads UTF-8 scripts without a BOM as the local "
        "ANSI code page; keep the launcher ASCII-only so powershell -File parses it."
    )
