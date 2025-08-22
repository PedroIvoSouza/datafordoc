# -*- coding: utf-8 -*-
import csv, sys, json
from pathlib import Path
from typing import Dict, Any
from src.run_utils import (
    download, extract_text_any, quick_tags,
    ensure_sqlite, upsert_doc, build_record_from_llmjson, regex_fallback,
    DATA_OUT
)
from src.llm_extract import extract_structured

def process_row(row: Dict[str, str]) -> Dict[str, Any]:
    uf = (row.get("uf") or "").strip().upper()
    fonte = (row.get("fonte") or "").strip().upper()
    url = (row.get("url") or "").strip()
    data_publicacao = (row.get("data_publicacao") or "").strip()
    prog_hint = (row.get("programa_hint") or "").strip() or None

    base_fields = {
        "uf": uf, "fonte": fonte, "data_publicacao": data_publicacao,
        "programa_hint": prog_hint,
        "pdf_fonte": url if "PDF" in fonte else None,
        "sei_publicacao": url if "SEI_PUB_PDF" in fonte else None
    }

    print(f"\n=== Coletando: {uf} | {fonte} | {url} | data={data_publicacao} ===")
    path, ct = download(url)
    text = extract_text_any(path)

    if not text.strip():
        print("Aviso: texto vazio (talvez precise de OCR). Salvando mínimo.")
        llm_json = None
    else:
        llm_json = extract_structured(
            texto=text,
            uf=uf, fonte=fonte, data_publicacao=data_publicacao,
            pdf_fonte=base_fields["pdf_fonte"],
            sei_publicacao=base_fields["sei_publicacao"],
            programa_hint=prog_hint
        )

    if llm_json:
        record = build_record_from_llmjson(base_fields, llm_json, raw_text_path=path.with_suffix(".txt"))
    else:
        record = regex_fallback(text, base_fields, raw_text_path=path.with_suffix(".txt"))

    # salva texto bruto para auditoria
    try:
        path.with_suffix(".txt").write_text(text, encoding="utf-8", errors="ignore")
    except Exception:
        pass

    return record

def main(csv_path: str):
    db = ensure_sqlite()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rec = process_row(row)
                upsert_doc(db, rec)
                print("OK:", json.dumps({k:rec.get(k) for k in ["empresa","cnpj","programa","tipo_ato","nup","confidence"]}, ensure_ascii=False))
            except Exception as e:
                print("ERRO na linha:", row, "->", e)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python run.py seeds.csv")
        sys.exit(1)
    main(sys.argv[1])
