#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera un PDF de nóminas FICTICIAS para probar la herramienta sin usar datos reales.

    pip install reportlab
    python generar_ejemplo.py

Crea 'nominas_ejemplo_enero.pdf' con 5 hojas:
  · Álvaro Ruiz Ferrán      (2 hojas, una sola nómina)
  · María José López Díaz   (1 hoja)
  · Sergio Núñez Campos     (1 hoja)
  · Pepe Desconocido García (1 hoja, no está en plantilla -> _Sin identificar)
"""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

NOMINAS = [
    ("ALVARO RUIZ FERRAN", "12345678Z", "Delantero", "ENERO", 2025, 1, 2),
    ("ALVARO RUIZ FERRAN", "12345678Z", "Delantero", "ENERO", 2025, 2, 2),
    ("MARIA JOSE LOPEZ DIAZ", "87654321X", "Fisioterapeuta", "ENERO", 2025, 1, 1),
    ("SERGIO NUÑEZ CAMPOS", "11223344L", "Defensa", "ENERO", 2025, 1, 1),
    ("PEPE DESCONOCIDO GARCIA", "99999999Q", "Utillero", "ENERO", 2025, 1, 1),
]

SALIDA = "nominas_ejemplo_enero.pdf"


def hoja(c, nombre, dni, puesto, mes, anio, pagina, total):
    c.setFont("Helvetica-Bold", 15)
    c.drawString(55, 790, "CLUB DEPORTIVO EJEMPLO S.A.D.")
    c.setFont("Helvetica", 9)
    c.drawString(55, 776, "C.I.F. A00000000 · Avda. del Estadio 1 · 28000 Madrid")
    c.line(55, 768, 540, 768)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(55, 748, "RECIBO INDIVIDUAL JUSTIFICATIVO DEL PAGO DE SALARIOS")

    c.setFont("Helvetica", 10)
    c.drawString(55, 722, f"Trabajador: {nombre}")
    c.drawString(55, 707, f"N.I.F.: {dni}")
    c.drawString(55, 692, f"Categoría: {puesto}")
    c.drawString(55, 677, f"Periodo de liquidación: {mes} {anio}")
    c.drawString(400, 677, f"Hoja {pagina} de {total}")

    c.line(55, 665, 540, 665)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(55, 648, "DEVENGOS")
    c.setFont("Helvetica", 10)
    filas = [("Salario base", "3.100,00"), ("Complemento de puesto", "850,00"),
             ("Prima de partido", "300,00")]
    y = 630
    for concepto, importe in filas:
        c.drawString(70, y, concepto)
        c.drawRightString(540, y, importe + " EUR")
        y -= 16

    c.setFont("Helvetica-Bold", 10)
    c.drawString(55, y - 10, "TOTAL DEVENGADO")
    c.drawRightString(540, y - 10, "4.250,00 EUR")

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(55, 60, "Documento de ejemplo con datos ficticios. No tiene validez alguna.")


def main():
    c = canvas.Canvas(SALIDA, pagesize=A4)
    for datos in NOMINAS:
        hoja(c, *datos)
        c.showPage()
    c.save()
    print(f"Creado {SALIDA} con {len(NOMINAS)} hojas.")


if __name__ == "__main__":
    main()
