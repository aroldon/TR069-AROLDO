import { describe, expect, it } from "vitest";
import {
  associatedClientsMessage,
  formatBytes,
  inventoryValue,
  opticalHealthLabel,
  opticalInventoryMessage,
  wifiBand,
} from "./device-workbench";

describe("device workbench", () => {
  it("classifica rádio pelo canal e usa o índice apenas como fallback", () => {
    expect(wifiBand({ root: "x", ssid: "a", channel: "11", index: 8 })).toBe("24");
    expect(wifiBand({ root: "x", ssid: "a", channel: "36", index: 1 })).toBe("5");
  });

  it("rotula a saúde óptica e distingue inventário vazio de CPE offline", () => {
    expect(opticalHealthLabel("good")).toBe("Sinal bom");
    expect(opticalHealthLabel("overload")).toBe("Sinal sobrecarregado");
    expect(opticalHealthLabel(null)).toBeNull();
    expect(opticalInventoryMessage(true, false)).toBe("Nenhuma telemetria óptica neste inventário.");
    expect(opticalInventoryMessage(false, false)).toBe("Aguardando CPE online");
    expect(opticalInventoryMessage(true, true)).toBeNull();
    expect(associatedClientsMessage(true, 0)).toBe("Nenhum cliente associado a este rádio.");
    expect(associatedClientsMessage(false, 0)).toBe("Aguardando CPE online");
    expect(associatedClientsMessage(false, 2)).toBeNull();
  });

  it("formata contadores e diferencia atualização de indisponibilidade", () => {
    expect(formatBytes(2 ** 30)).toBe("1 GB");
    expect(formatBytes({} as unknown as number)).toBeNull();
    expect(inventoryValue(null, true, true)).toBe("Atualizando…");
    expect(inventoryValue(null, false, false)).toBe("Aguardando CPE online");
  });
});
