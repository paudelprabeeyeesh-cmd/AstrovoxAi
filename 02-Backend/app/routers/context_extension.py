import logging

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context-extension"])


@router.post("/context/extend")
async def extend_context_window(req: dict, user_id: str = Depends(require_verified_email)):
    base_seq_len = req.get("base_seq_len", 32768)
    target_seq_len = req.get("target_seq_len", 1048576)
    method = req.get("method", "yarn")
    methods = {
        "rope": {"description": "Rotary Position Embedding", "stretch_factor": 1.0},
        "ntk_aware": {"description": "NTK-Aware Interpolation", "stretch_factor": 4.0},
        "yarn": {"description": "YaRN (Yet another RoPE Extension)", "stretch_factor": 8.0},
        "xpos": {"description": " extrapolated Rotary Position Embedding", "stretch_factor": 16.0},
    }
    if method not in methods:
        raise HTTPException(status_code=400, detail=f"Unknown method. Available: {list(methods.keys())}")
    base = methods[method]
    stretch_factor = base["stretch_factor"]
    extended_len = min(target_seq_len, base_seq_len * stretch_factor)
    lost_in_middle_mitigation = req.get("lost_in_middle_mitigation", True)
    return {
        "base_seq_len": base_seq_len,
        "target_seq_len": target_seq_len,
        "method": method,
        "stretch_factor": stretch_factor,
        "extended_seq_len": extended_len,
        "lost_in_middle_mitigation": lost_in_middle_mitigation,
        "description": base["description"],
        "efficiency": round(extended_len / base_seq_len, 2),
    }


@router.get("/context/methods")
async def get_context_methods(user_id: str = Depends(require_verified_email)):
    return {
        "methods": {
            "rope": {"name": "RoPE", "description": "Rotary Position Embedding", "max_stretch": 1.0},
            "ntk_aware": {"name": "NTK-Aware", "description": "NTK-Aware Interpolation", "max_stretch": 4.0},
            "yarn": {"name": "YaRN", "description": "Yet another RoPE Extension", "max_stretch": 8.0},
            "xpos": {"name": "XPos", "description": "Extrapolated Position Embedding", "max_stretch": 16.0},
        },
        "current_default": "yarn",
    }


@router.post("/context/lost-in-middle")
async def mitigate_lost_in_middle(req: dict, user_id: str = Depends(require_verified_email)):
    documents = req.get("documents", [])
    importance_scores = req.get("importance_scores", {})
    ranked = []
    for doc in documents:
        relevance = doc.get("relevance", 0.5)
        score = relevance * importance_scores.get(doc.get("id", ""), 1.0)
        ranked.append({"doc": doc, "score": score})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    reordered = []
    n = len(ranked)
    for i, item in enumerate(ranked):
        if i < n // 3:
            pos = i * 2
        elif i < 2 * n // 3:
            pos = n // 2 + (i - n // 3)
        else:
            pos = n - 1 - (n - i - 1) * 2
        pos = max(0, min(pos, n - 1))
        item["position"] = pos
        reordered.append(item)
    reordered.sort(key=lambda x: x["position"])
    return {
        "original_count": len(documents),
        "reordered": [{"doc_id": r["doc"].get("id"), "position": r["position"], "score": r["score"]} for r in reordered],
        "strategy": "beginning_middle_end",
    }
