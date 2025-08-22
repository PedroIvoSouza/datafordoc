# -*- coding: utf-8 -*-
import csv, sqlite3
from pathlib import Path

DATA_OUT = Path(__file__).resolve().parents[0] / "data" / "outputs"
DB = DATA_OUT / "docs.sqlite3"
CSV_OUT = DATA_OUT / "atos.csv"

con = sqlite3.connect(DB)
cur = con.cursor()

rows = cur.execute("""
SELECT
  uf, fonte, data_publicacao, empresa, cnpj, programa, tipo_ato, nup,
  fundamentos, credito_presumido_percent, reducao_base_percent, diferimento,
  vigencia_inicio, vigencia_fim, pdf_fonte, sei_publicacao, confidence
FROM docs
ORDER BY data_publicacao, uf;
""").fetchall()

headers = ["uf","fonte","data_publicacao","empresa","cnpj","programa","tipo_ato","nup",
           "fundamentos","credito_presumido_percent","reducao_base_percent","diferimento",
           "vigencia_inicio","vigencia_fim","pdf_fonte","sei_publicacao","confidence"]

with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(headers)
    for r in rows:
        w.writerow(r)

print(f"[OK] Exportado: {CSV_OUT}")
