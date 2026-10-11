from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.acs.actions.base import ActionContext
from app.acs.actions.optical import optical_refresh
from app.acs.actions.params import params_get
from app.acs.actions.wifi import wifi_clients_get, wifi_set
from app.cpe.params import Cap
from app.integrations.acs.genieacs_client import GenieAcsResponse
from app.models.settings import AppSettings


def _huawei():
    return {
        "_deviceId": {"_Manufacturer": "Huawei Technologies Co., Ltd.", "_ProductClass": "EG8145V5"},
        "InternetGatewayDevice": {
            "IPPingDiagnostics": {"DiagnosticsState": {"_value": "None"}},
            "WANDevice": {
                "1": {"X_GponInterafceConfig": {"RXPower": {"_value": -20}}},
            },
            "LANDevice": {
                "1": {
                    "WLANConfiguration": {
                        "1": {
                            "SSID": {"_value": "Casa"},
                            "Enable": {"_value": True},
                            "SSIDAdvertisementEnabled": {"_value": True},
                            "AssociatedDevice": {
                                "3": {
                                    "AssociatedDeviceMACAddress": {"_value": "AA:BB:CC:00:11:22"},
                                    "SignalStrength": {"_value": -61},
                                    "AssociatedDeviceAuthenticationState": {"_value": False},
                                }
                            },
                        }
                    }
                }
            },
        },
    }


class FakeClient:
    def __init__(self, device):
        self.device = device
        self.created = []

    async def get_device(self, _device_id, *, projection=None):
        return self.device

    async def create_task(self, device_id, payload, *, connection_request, timeout_ms):
        self.created.append((device_id, payload, connection_request, timeout_ms))
        return GenieAcsResponse(status_code=200, json={})


def _context(client: FakeClient, params=None):
    return ActionContext(
        device_id="cpe-1",
        params=params or {},
        client=client,
        db=SimpleNamespace(),
        auth=SimpleNamespace(),
        server=SimpleNamespace(),
    )


async def test_optical_refresh_targets_only_the_existing_container():
    client = FakeClient(_huawei())

    result = await optical_refresh(_context(client))

    assert result["ok"] is True
    payload = client.created[0][1]
    assert payload == {
        "name": "refreshObject",
        "objectName": "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig",
    }
    assert "X_HW_DEBUG" not in payload["objectName"]
    assert "X_CT-COM" not in payload["objectName"]
    assert client.created[0][2] is True


async def test_optical_refresh_refuses_a_device_without_optical_container():
    client = FakeClient({"_deviceId": {"_Manufacturer": "Generic", "_ProductClass": "IGD"}})

    with pytest.raises(HTTPException) as exc:
        await optical_refresh(_context(client))

    assert exc.value.status_code == 400
    assert client.created == []


async def test_wifi_clients_get_reads_associated_devices():
    client = FakeClient(_huawei())

    result = await wifi_clients_get(_context(client))

    assert result["ok"] is True
    assert result["clients"][0]["mac"] == "AA:BB:CC:00:11:22"
    assert result["clients"][0]["ssid"] == "Casa"
    assert result["clients"][0]["authenticated"] is False
    assert client.created == []


async def test_wifi_clients_get_is_empty_without_associations():
    client = FakeClient({"_deviceId": {"_Manufacturer": "Generic", "_ProductClass": "IGD"}})

    result = await wifi_clients_get(_context(client))

    assert result == {"ok": True, "clients": []}


async def test_wifi_set_skips_leaves_that_are_not_on_the_device():
    device = {
        "_deviceId": {"_Manufacturer": "Generic", "_ProductClass": "IGD"},
        "InternetGatewayDevice": {
            "LANDevice": {
                "1": {"WLANConfiguration": {"1": {"SSID": {"_value": "Casa"}, "Enable": {"_value": True}}}}
            }
        },
    }
    client = FakeClient(device)
    root = "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1"

    await wifi_set(
        _context(
            client,
            {"root": root, "ssid": "Nova", "hidden": True, "maxClients": 8, "txPower": 40},
        )
    )

    values = {row[0]: row[1] for row in client.created[0][1]["parameterValues"]}
    assert values[f"{root}.SSID"] == "Nova"
    assert f"{root}.SSIDAdvertisementEnabled" not in values
    assert f"{root}.MaxAssociatedDevices" not in values
    assert f"{root}.TransmitPower" not in values


async def test_params_get_resolves_allowlist_and_rejects_free_paths():
    client = FakeClient(_huawei())

    result = await params_get(
        _context(
            client,
            {"capabilities": [Cap.OPTICAL_CONTAINER, Cap.PING_ROOT, Cap.TRACEROUTE_ROOT]},
        )
    )

    assert result["ok"] is True
    payload = client.created[0][1]
    assert payload["name"] == "getParameterValues"
    assert payload["parameterNames"] == [
        "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig",
        "InternetGatewayDevice.IPPingDiagnostics",
        "InternetGatewayDevice.TraceRouteDiagnostics",
    ]
    assert client.created[0][2] is True

    client.created.clear()
    with pytest.raises(HTTPException) as free_path:
        await params_get(
            _context(client, {"capabilities": ["InternetGatewayDevice.DeviceInfo.SoftwareVersion"]})
        )
    assert free_path.value.status_code == 400
    with pytest.raises(HTTPException) as paths_key:
        await params_get(
            _context(client, {"paths": ["Device.Optical.Interface"], "capabilities": [Cap.PING_ROOT]})
        )
    assert paths_key.value.status_code == 400
    assert client.created == []


def test_app_settings_optical_defaults():
    columns = AppSettings.__table__.c
    assert columns.optical_rx_no_signal_dbm.default.arg == -30.0
    assert columns.optical_rx_critical_dbm.default.arg == -27.0
    assert columns.optical_rx_warning_dbm.default.arg == -24.0
    assert columns.optical_rx_overload_dbm.default.arg == -8.0
