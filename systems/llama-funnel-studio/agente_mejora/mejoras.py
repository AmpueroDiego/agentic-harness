#!/usr/bin/env python3
"""
mejoras.py — registro de mejoras del sistema, en Excel

Cada observación que sale trabajando con el sistema se anota aquí con su mejora,
su prioridad y su estado. El objetivo es que nada de lo que se detecta se pierda
entre conversaciones.

Vive fuera de `tools/` a propósito: `tools/` es la mitad determinista del pipeline
de extracción, y esto no extrae nada — es meta sobre el propio sistema.

**El protocolo — qué se anota, qué no, y cuándo se marca como aplicada — está en
SKILL.md, al lado de este archivo.** Aquí solo vive el registro y su formato.

Uso:
    python agente_mejora/mejoras.py                 # crea o actualiza el Excel
    python agente_mejora/mejoras.py --ruta X.xlsx   # otro destino

**Es aditivo y no destructivo.** Si el archivo ya existe, solo añade las filas
cuyo ID no esté presente. Lo que hayas editado a mano — cambiar un estado, añadir
una nota, escribir filas nuevas — se conserva intacto.

Para anotar una mejora nueva: añade una tupla a REGISTRO con un ID libre y vuelve
a correrlo. O escríbela directamente en el Excel; el script no la tocará.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent

COLUMNAS = [
    ("ID", 8), ("Fecha", 12), ("Área", 18), ("Archivo", 30),
    ("Observación", 62), ("Mejora a aplicar", 62), ("Por qué importa", 58),
    ("Prioridad", 11), ("Estado", 13), ("Constancia", 34),
]

F = "2026-07-26"

# ID, fecha, área, archivo, observación, mejora, por qué importa, prioridad, estado, constancia
REGISTRO: list[tuple] = []  # Local observations belong to the adopting project.


def construir(ruta: Path) -> None:
    cab_fill = PatternFill("solid", fgColor="1F2937")
    cab_font = Font(color="FFFFFF", bold=True, size=11)
    colores = {
        "Aplicada":  PatternFill("solid", fgColor="D1FAE5"),
        "Pendiente": PatternFill("solid", fgColor="FEF3C7"),
        "Decidida":  PatternFill("solid", fgColor="DBEAFE"),
        "Descartada": PatternFill("solid", fgColor="E5E7EB"),
    }
    prio = {
        "Alta":  PatternFill("solid", fgColor="FEE2E2"),
        "Media": PatternFill("solid", fgColor="FEF3C7"),
        "Baja":  PatternFill("solid", fgColor="F3F4F6"),
    }

    if ruta.exists():
        wb = load_workbook(ruta)
        ws = wb["Mejoras"] if "Mejoras" in wb.sheetnames else wb.active
        vistos = {ws.cell(r, 1).value for r in range(2, ws.max_row + 1)}
        nuevas = [f for f in REGISTRO if f[0] not in vistos]
        if not nuevas:
            print(f"  sin novedades — {ruta.name} ya tiene las {len(vistos)} filas")
            return
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Mejoras"
        ws.append([c for c, _ in COLUMNAS])
        for i, (_, ancho) in enumerate(COLUMNAS, 1):
            ws.column_dimensions[get_column_letter(i)].width = ancho
            c = ws.cell(1, i)
            c.fill, c.font = cab_fill, cab_font
            c.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
        ws.row_dimensions[1].height = 28
        ws.freeze_panes = "A2"
        nuevas = REGISTRO

    for fila in nuevas:
        ws.append(list(fila))
        r = ws.max_row
        for i in range(1, len(COLUMNAS) + 1):
            ws.cell(r, i).alignment = Alignment(vertical="top", wrap_text=True)
        ws.cell(r, 1).font = Font(bold=True)
        ws.cell(r, 8).fill = prio.get(fila[7], prio["Baja"])
        ws.cell(r, 9).fill = colores.get(fila[8], colores["Pendiente"])
        ws.cell(r, 9).font = Font(bold=True)
        ws.row_dimensions[r].height = 92

    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNAS))}{ws.max_row}"
    wb.save(ruta)
    print(f"  {ruta.name}: +{len(nuevas)} filas, {ws.max_row - 1} en total")


def main() -> None:
    p = argparse.ArgumentParser(description="Registro de mejoras del sistema, en Excel.")
    p.add_argument("--ruta", default=str(AQUI / "agente_mejora.xlsx"))
    construir(Path(p.parse_args().ruta))


if __name__ == "__main__":
    main()
