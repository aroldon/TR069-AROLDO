"""Leitura pontual de capacidades do catálogo. Sem path livre."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.acs.actions.base import ActionContext, action, create_named_task
from app.cpe.extract import parameter_names_for_capabilities
from app.cpe.params import Cap

PARAMS_GET_CAPABILITIES = (
    Cap.OPTICAL_CONTAINER,
    Cap.PING_ROOT,
    Cap.TRACEROUTE_ROOT,
)


@action(
    "params_get",
    permission="acs.devices.write",
    notes="getParameterValues da allowlist óptica/ping/traceroute",
)
async def params_get(ctx: ActionContext) -> dict[str, Any]:
    if "paths" in ctx.params or "parameterNames" in ctx.params:
        raise HTTPException(status_code=400, detail="Paths livres não são aceitos")
    raw = ctx.params.get("capabilities")
    if not isinstance(raw, list) or not raw:
        raise HTTPException(status_code=400, detail="capabilities obrigatório")
    if any(not isinstance(item, str) for item in raw):
        raise HTTPException(status_code=400, detail="capabilities deve listar capacidades do catálogo")
    if any(item not in PARAMS_GET_CAPABILITIES for item in raw):
        raise HTTPException(status_code=400, detail="Capacidade fora da allowlist")
    names = parameter_names_for_capabilities(await ctx.load_device(), list(dict.fromkeys(raw)))
    if not names:
        raise HTTPException(status_code=400, detail="Nenhum parâmetro resolvido para este CPE")
    return await create_named_task(
        ctx,
        {"name": "getParameterValues", "parameterNames": names},
        timeout_ms=25000,
    )
