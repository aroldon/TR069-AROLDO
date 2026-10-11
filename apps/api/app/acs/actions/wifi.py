"""Wi‑Fi set / get."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.acs.actions.base import ActionContext, action, set_parameter_values
from app.cpe.extract import (
    WifiParameterError,
    extract_wifi_clients,
    extract_wifi_radios,
    wifi_set_parameter_values,
)


def _optional_bool(params: dict[str, Any], key: str) -> bool | None:
    if key not in params or params[key] is None:
        return None
    value = params[key]
    if isinstance(value, bool):
        return value
    raise HTTPException(status_code=400, detail=f"{key} deve ser booleano")


def _optional_int(params: dict[str, Any], key: str) -> int | None:
    if key not in params or params[key] in (None, ""):
        return None
    value = params[key]
    if isinstance(value, bool):
        raise HTTPException(status_code=400, detail=f"{key} inválido")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{key} inválido") from exc


@action("wifi_get", notes="Extrai rádios/SSID do inventário via catálogo CPE")
async def wifi_get(ctx: ActionContext) -> dict[str, Any]:
    return {"ok": True, "radios": extract_wifi_radios(await ctx.load_device())}


@action(
    "wifi_clients_get",
    notes="Clientes AssociatedDevice dos rádios já resolvidos; não substitui hosts_get",
)
async def wifi_clients_get(ctx: ActionContext) -> dict[str, Any]:
    return {"ok": True, "clients": extract_wifi_clients(await ctx.load_device())}


@action("wifi_set", permission="acs.devices.write", notes="SPV SSID/senha e folhas opcionais já presentes no CPE")
async def wifi_set(ctx: ActionContext) -> dict[str, Any]:
    pvs = ctx.params.get("parameterValues")
    if not isinstance(pvs, list):
        root = str(ctx.params.get("root") or "").strip()
        if not root:
            raise HTTPException(status_code=400, detail="root ou parameterValues obrigatório")
        dev = await ctx.load_device()
        try:
            pvs = wifi_set_parameter_values(
                root,
                ssid=None if ctx.params.get("ssid") is None else str(ctx.params.get("ssid")),
                password=str(ctx.params["password"]) if ctx.params.get("password") else None,
                channel=int(ctx.params["channel"]) if ctx.params.get("channel") not in (None, "") else None,
                bandwidth=str(ctx.params["bandwidth"]) if ctx.params.get("bandwidth") else None,
                enabled=bool(ctx.params["enabled"]) if ctx.params.get("enabled") is not None else None,
                hidden=_optional_bool(ctx.params, "hidden"),
                max_clients=_optional_int(ctx.params, "maxClients"),
                auth_mode=str(ctx.params["authMode"]) if ctx.params.get("authMode") else None,
                encryption=str(ctx.params["encryption"]) if ctx.params.get("encryption") else None,
                tx_power=_optional_int(ctx.params, "txPower"),
                dev=dev,
            )
        except WifiParameterError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not pvs:
        raise HTTPException(status_code=400, detail="Nenhuma alteração Wi‑Fi")
    return await set_parameter_values(ctx.client, ctx.device_id, pvs)
