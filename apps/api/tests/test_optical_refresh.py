from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.acs.actions.base import ActionContext
from app.acs.actions.optical import optical_refresh
from app.acs.actions.wifi import wifi_set
from app.integrations.acs.genieacs_client import GenieAcsResponse


class FakeClient:
    def __init__(self, device):
        self.device = device
        self.created = []

    async def get_device(self, _device_id, *, projection=None):
        return self.device

    async def create_task(self, device_id, payload, *, connection_request, timeout_ms):
        self.created.append((device_id, payload, connection_request, timeout_ms))
        return GenieAcsResponse(status_code=200, json={})


def _ctx(client: FakeClient, params=None):
    return ActionContext(
        device_id="ABC",
        params=params or {},
        client=client,
        db=None,
        auth=SimpleNamespace(require=lambda _perm: None),
        server=SimpleNamespace(id="srv"),
    )


def _zte_optical():
    return {
        "_deviceId": {"_Manufacturer": "ZTE", "_ProductClass": "F670L"},
        "InternetGatewayDevice": {
            "X_CT-COM_GponInterfaceConfig": {
                "Stats": {"RxPower": {"_value": -20}, "TxPower": {"_value": 2}}
            }
        },
    }


async def test_optical_refresh_targets_only_the_existing_container():
    client = FakeClient(_zte_optical())
    result = await optical_refresh(_ctx(client))
    assert result["ok"] is True
    assert len(client.created) == 1
    payload = client.created[0][1]
    assert payload["name"] == "refreshObject"
    assert payload["objectName"] == "InternetGatewayDevice.X_CT-COM_GponInterfaceConfig.Stats"
    assert "X_HW_DEBUG" not in payload["objectName"]
    assert "X_Realtek" not in payload["objectName"]


async def test_optical_refresh_refuses_when_no_container_exists():
    client = FakeClient({"_deviceId": {"_Manufacturer": "Generic", "_ProductClass": "IGD"}})
    with pytest.raises(HTTPException) as exc:
        await optical_refresh(_ctx(client))
    assert exc.value.status_code == 400
    assert client.created == []


async def test_wifi_set_rejects_transmit_power_outside_steps():
    device = {
        "_deviceId": {"_Manufacturer": "Generic", "_ProductClass": "IGD"},
        "InternetGatewayDevice": {
            "LANDevice": {
                "1": {
                    "WLANConfiguration": {
                        "1": {"SSID": {"_value": "Casa"}, "TransmitPower": {"_value": 100}}
                    }
                }
            }
        },
    }
    client = FakeClient(device)
    with pytest.raises(HTTPException) as exc:
        await wifi_set(
            _ctx(
                client,
                {
                    "root": "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1",
                    "transmitPower": 50,
                },
            )
        )
    assert exc.value.status_code == 400
    assert client.created == []
