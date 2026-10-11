"""Atualiza só o container óptico que o perfil deste CPE já resolveu."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.acs.actions.base import ActionContext, action, create_named_task
from app.cpe.extract import first_optical_container


@action(
    "optical_refresh",
    permission="acs.devices.write",
    notes="refreshObject no primeiro Cap.OPTICAL_CONTAINER presente no inventário",
)
async def optical_refresh(ctx: ActionContext) -> dict[str, Any]:
    container = first_optical_container(await ctx.load_device())
    if not container:
        raise HTTPException(status_code=400, detail="Este CPE não tem container óptico no inventário.")
    return await create_named_task(
        ctx,
        {"name": "refreshObject", "objectName": container},
        timeout_ms=25000,
    )
