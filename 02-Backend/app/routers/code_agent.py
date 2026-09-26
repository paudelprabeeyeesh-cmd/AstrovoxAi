import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from ..coding.agent import CodingAgent
from ..coding.project_graph import ProjectGraph

logger = logging.getLogger(__name__)

router = APIRouter(tags=["coding-agent"])


@router.post("/coding/index")
async def index_repo(repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        result = agent.build_index()
        return result
    except Exception as exc:
        logger.error("Coding agent indexing failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/graph")
async def build_graph(repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        result = agent.build_graph()
        return result
    except Exception as exc:
        logger.error("Coding agent graph build failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/coding/symbol")
async def find_symbol(symbol: str, repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        agent.build_index()
        results = agent.index.search_symbols(symbol)
        return {"symbol": symbol, "references": results}
    except Exception as exc:
        logger.error("Symbol search failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/coding/file")
async def read_file(file_path: str, repo_path: str, offset: int = 1, limit: int = 200, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        full_path = agent.index.repo_path + os.sep + file_path
        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        start = max(0, offset - 1)
        end = min(len(lines), start + limit)
        return {"file": file_path, "content": "".join(lines[start:end])}
    except Exception as exc:
        logger.error("File read failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/edit")
async def edit_file(file_path: str, old_string: str, new_string: str, repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        result = agent.multi_edit.apply_edit(file_path, old_string, new_string)
        return result
    except Exception as exc:
        logger.error("File edit failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/multi-edit")
async def multi_edit(edits: list[dict[str, str]], repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        result = agent.multi_edit.apply_edits(edits)
        return result
    except Exception as exc:
        logger.error("Multi-edit failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/run")
async def run_command(command: str, repo_path: str, timeout: int = 30, user_id: str = Depends(require_verified_email)):
    try:
        import subprocess

        result = subprocess.run(
            command, shell=True, cwd=repo_path, capture_output=True, text=True, timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:10000],
            "stderr": result.stderr[:10000],
            "return_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {timeout}s"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/coding/analyze")
async def analyze_dependencies(repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        return agent.analyze_dependencies()
    except Exception as exc:
        logger.error("Dependency analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/refactor")
async def suggest_refactors(file_path: str, repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        return agent.suggest_refactors(file_path)
    except Exception as exc:
        logger.error("Refactor suggestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/tests")
async def generate_tests(file_path: str, symbol_name: str, repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        return agent.generate_tests(file_path, symbol_name)
    except Exception as exc:
        logger.error("Test generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/bugs")
async def scan_bugs(file_path: str, repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        return agent.scan_bugs(file_path)
    except Exception as exc:
        logger.error("Bug scan failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/review")
async def review_file(file_path: str, repo_path: str, diff: str | None = None, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        if diff:
            return agent.review_diff(diff)
        return agent.review_file(file_path)
    except Exception as exc:
        logger.error("Review failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/docs")
async def generate_docs(file_path: str, repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        return agent.generate_docs(file_path)
    except Exception as exc:
        logger.error("Doc generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/api")
async def infer_api(file_paths: list[str], repo_path: str, language: str = "python", user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        spec = agent.infer_api(file_paths)
        client = agent.generate_api_client(spec, language)
        return {"spec": spec, "client": client}
    except Exception as exc:
        logger.error("API inference failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/architecture")
async def architecture_analysis(repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        return agent.architecture_analysis()
    except Exception as exc:
        logger.error("Architecture analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/task")
async def execute_task(repo_path: str, task: str, target: str | None = None, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        return agent.execute_task(task, target)
    except Exception as exc:
        logger.error("Coding task failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/lsp/definition")
async def lsp_definition(file_path: str, line: int, character: int, repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        return agent.go_to_definition(file_path, line, character)
    except Exception as exc:
        logger.error("LSP definition failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/coding/lsp/references")
async def lsp_references(file_path: str, line: int, character: int, repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodingAgent(repo_path=repo_path)
        return agent.find_references(file_path, line, character)
    except Exception as exc:
        logger.error("LSP references failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
