from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_frontend_raw_api_calls_stay_in_endpoint_modules():
    pattern = re.compile(r"\bapi\.(get|post|put|delete)\(")
    allowed = ROOT / "frontend" / "src" / "api" / "endpoints"
    offenders = []

    for path in (ROOT / "frontend" / "src").rglob("*"):
        if path.suffix not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        if allowed in path.parents:
            continue
        if pattern.search(_read(path)):
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_frontend_endpoint_modules_are_only_used_by_feature_hooks():
    pattern = re.compile(r'from\s+["\']@/api/endpoints/')
    allowed_dirs = [
        ROOT / "frontend" / "src" / "features",
        ROOT / "frontend" / "src" / "api" / "endpoints",
    ]
    offenders = []

    for path in (ROOT / "frontend" / "src").rglob("*"):
        if path.suffix not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        if any(allowed in path.parents for allowed in allowed_dirs):
            continue
        if pattern.search(_read(path)):
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_backend_collection_access_stays_out_of_runtime_layers():
    pattern = re.compile(r"\bdb\.[A-Za-z_][A-Za-z0-9_]*")
    checked_dirs = [
        ROOT / "backend" / "app" / "api" / "endpoints",
        ROOT / "backend" / "app" / "services",
        ROOT / "backend" / "app" / "integrations",
    ]
    offenders = []

    for directory in checked_dirs:
        for path in directory.rglob("*.py"):
            if pattern.search(_read(path)):
                offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_docs_do_not_reference_deleted_backend_entrypoint():
    docs = [
        ROOT / "README.md",
        ROOT / "ARCHITECTURE.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "IMPLEMENTATION_ROADMAP.md",
        ROOT / "OCR_PIPELINE.md",
        ROOT / "backend" / "app" / "ARCHITECTURE.md",
    ]
    offenders = [
        str(path.relative_to(ROOT))
        for path in docs
        if path.exists() and "server:app" in _read(path)
    ]

    assert offenders == []
