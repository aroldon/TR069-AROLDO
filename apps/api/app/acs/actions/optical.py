"""Refresh da subtree óptica já resolvida para o CPE."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.acs.actions.base import ActionContext, action, create_named_task
from app.cpe.params import Cap
from app.cpe.profiles import candidates_for
from app.cpe.tree import first_existing_path


@action(
    "optical_refresh",
    permission="acs.access",
    notes="refreshObject apenas no container óptico presente no inventário",
    audit=False,
)
async def optical_refresh(ctx: ActionContext) -> dict[str, Any]:
    dev = await ctx.load_device()
    candidates = [path for path in candidates_for(dev, Cap.OPTICAL_CONTAINER) if "{" not in path]
    target = first_existing_path(dev, candidates, require_value=False)
    if not target:
        raise HTTPException(
            status_code=400,
            detail="Nenhum container óptico no inventário deste CPE",
        )
    return await create_named_task(
        ctx,
        {"name": "refreshObject", "objectName": target.rstrip(".")},
        timeout_ms=25000,
    )
