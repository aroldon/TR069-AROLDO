"""Wi‑Fi set / get."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.acs.actions.base import ActionContext, action, set_parameter_values
from app.cpe.extract import extract_wifi_clients, extract_wifi_radios, wifi_set_parameter_values
from app.cpe.params import Cap
from app.cpe.profiles import candidates_for
from app.cpe.tree import first_existing_path

_TX_POWER_STEPS = {0, 20, 40, 60, 80, 100}


@action("wifi_get", notes="Extrai rádios/SSID do inventário via catálogo CPE")
async def wifi_get(ctx: ActionContext) -> dict[str, Any]:
    return {"ok": True, "radios": extract_wifi_radios(await ctx.load_device())}


def _existing_leaf(dev: dict[str, Any], root: str, capability: str) -> str | None:
    paths = [tmpl.replace("{root}", root) for tmpl in candidates_for(dev, capability)]
    return first_existing_path(dev, paths, require_value=False)


@action("wifi_clients_get", notes="Clientes associados ao rádio (AssociatedDevice)", audit=False)
async def wifi_clients_get(ctx: ActionContext) -> dict[str, Any]:
    return {"ok": True, "clients": extract_wifi_clients(await ctx.load_device())}


@action("wifi_set", permission="acs.devices.write", notes="SPV SSID/senha; paths via Cap.WIFI_*")
async def wifi_set(ctx: ActionContext) -> dict[str, Any]:
    pvs = ctx.params.get("parameterValues")
    if not isinstance(pvs, list):
        root = str(ctx.params.get("root") or "").strip()
        if not root:
            raise HTTPException(status_code=400, detail="root ou parameterValues obrigatório")
        dev = await ctx.load_device()
        hidden = bool(ctx.params["hidden"]) if "hidden" in ctx.params else None
        max_clients = None
        if ctx.params.get("maxClients") not in (None, ""):
            try:
                max_clients = int(ctx.params["maxClients"])
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail="Máximo de clientes inválido") from exc
            if not 1 <= max_clients <= 128:
                raise HTTPException(status_code=400, detail="Máximo de clientes deve ficar entre 1 e 128")
            if not _existing_leaf(dev, root, Cap.WIFI_MAX_CLIENTS):
                raise HTTPException(status_code=400, detail="Este CPE não informa limite de clientes Wi-Fi")
        transmit_power = None
        if ctx.params.get("transmitPower") not in (None, ""):
            try:
                transmit_power = int(ctx.params["transmitPower"])
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail="Potência de transmissão inválida") from exc
            if transmit_power not in _TX_POWER_STEPS:
                raise HTTPException(
                    status_code=400,
                    detail="Potência de transmissão deve ser 0, 20, 40, 60, 80 ou 100",
                )
            if not _existing_leaf(dev, root, Cap.WIFI_TX_POWER):
                raise HTTPException(status_code=400, detail="Este CPE não informa potência de transmissão")
        if hidden is not None and not _existing_leaf(dev, root, Cap.WIFI_HIDDEN):
            raise HTTPException(status_code=400, detail="Este CPE não informa se o SSID está oculto")
        pvs = wifi_set_parameter_values(
            root,
            ssid=None if ctx.params.get("ssid") is None else str(ctx.params.get("ssid")),
            password=str(ctx.params["password"]) if ctx.params.get("password") else None,
            channel=int(ctx.params["channel"]) if ctx.params.get("channel") not in (None, "") else None,
            bandwidth=str(ctx.params["bandwidth"]) if ctx.params.get("bandwidth") else None,
            enabled=bool(ctx.params["enabled"]) if ctx.params.get("enabled") is not None else None,
            hidden=hidden,
            max_clients=max_clients,
            transmit_power=transmit_power,
            dev=dev,
        )
    if not pvs:
        raise HTTPException(status_code=400, detail="Nenhuma alteração Wi‑Fi")
    return await set_parameter_values(ctx.client, ctx.device_id, pvs)
