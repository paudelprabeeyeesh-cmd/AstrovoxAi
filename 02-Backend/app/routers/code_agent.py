import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from ..code_agent import CodeAgent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["code-agent"])


@router.post("/code/agent/index")
async def index_repo(repo_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodeAgent(repo_path=repo_path)
        result = agent.index_repo()
        return result
    except Exception as e:
        logger.error(f"Code agent indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/code/agent/references")
async def find_references(symbol: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodeAgent(repo_path=".")
        results = agent.find_references(symbol)
        return {"symbol": symbol, "references": results}
    except Exception as e:
        logger.error(f"Code agent reference search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/code/agent/file")
async def read_file(file_path: str, offset: int = 1, limit: int = 200, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodeAgent(repo_path=".")
        content = agent.read_file(file_path, offset=offset, limit=limit)
        return {"file": file_path, "content": content}
    except Exception as e:
        logger.error(f"Code agent file read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code/agent/edit")
async def edit_file(file_path: str, old_string: str, new_string: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodeAgent(repo_path=".")
        result = agent.edit_file(file_path, old_string, new_string)
        return result
    except Exception as e:
        logger.error(f"Code agent file edit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code/agent/run")
async def run_command(command: str, timeout: int = 30, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodeAgent(repo_path=".")
        result = agent.run_command(command, timeout=timeout)
        return result
    except Exception as e:
        logger.error(f"Code agent command execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code/agent/verify")
async def verify_syntax(file_path: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodeAgent(repo_path=".")
        result = agent.verify_syntax(file_path)
        return result
    except Exception as e:
        logger.error(f"Code agent syntax verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code/agent/checkpoint")
async def create_checkpoint(message: str, user_id: str = Depends(require_verified_email)):
    try:
        agent = CodeAgent(repo_path=".")
        result = agent.create_checkpoint(message)
        return result
    except Exception as e:
        logger.error(f"Code agent checkpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
