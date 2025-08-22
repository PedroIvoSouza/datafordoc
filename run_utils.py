# -*- coding: utf-8 -*-
import os, re, json, hashlib, time
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
from rapidfuzz import fuzz

# ============ Paths ============
BASE = Path(__file__).resolve().parents[1]
DATA_IN = BASE / "data" / "inputs"
DATA_OUT = BASE / "data" / "outputs"
DATA_IN.mkdir(parents=True, exist_ok=True)
DATA_OUT.mkdir(parents=True, exist_ok=True)

# ============ Regex úteis ============
RE_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
RE_NUP  = re.compile(r"\b\d{5}\.\d{6}/\d{4}-\d{2}\b")

TERMS_ICMS = re.compile(r"(incentiv|benef[ií]ci|cr[eé]dito presumido|redu[cç][aã]o da base|diferiment|ICMS|Programa)", re.I)

# ============ Helpers ============
def sha256_bytes(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()

def safe_filename(url: str) -> str:
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
    path = urlparse(url).path
    name = os.path.basename(path) or "index"
    return f"{name}_{h}"

def download(url: str, timeout: int = 90) -> Tuple[Path, str]:
    """Baixa conteúdo (PDF/HTML). Retorna (caminho_arquivo, content_type)."""
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "IA-DOE-SEI/1.0"})
    r.raise_for_status()
    ct = r.headers.get("Content-Type", "").lower()
    fn = safe_filename(url)
    if "pdf" in ct or url.lower().endswith(".pdf"):
        dest = DATA_IN / f"{fn}.pdf"
    else:
        dest = DATA_IN / f"{fn}.html"
    dest.write_bytes(r.content)
    return dest, ct

def extract_text_any(path: Path) -> str:
    """Extrai texto de PDF (pdfminer) ou HTML (BeautifulSoup)."""
    if path.suffix.lower() == ".pdf":
        try:
            return extract_text(str(path)) or ""
        except Exception:
            return ""
    else:
        html = path.read_text("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "lxml")
        # remove scripts/styles
        for tag in soup(["script","style","noscript"]):
            tag.decompose()
        return soup.get_text("\n")

def quick_tags(text: str) -> Dict[str, Any]:
    """Heurísticas rápidas (regex) para apoiar o fallback e notas."""
    cnpjs = list(set(RE_CNPJ.findall(text)))
    nups  = list(set(RE_NUP.findall(text)))
    has_icms_terms = bool(TERMS_ICMS.search(text))
    return {"cnpjs": cnpjs, "nups": nups, "has_icms_terms": has_icms_terms}

def ensure_sqlite():
    import sqlite3
    db = sqlite3.connect(DATA_OUT / "docs.sqlite3")
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS docs (
      doc_id TEXT PRIMARY KEY,
      uf TEXT, fonte TEXT, data_publicacao TEXT,
      empresa TEXT, cnpj TEXT, programa TEXT, tipo_ato TEXT, nup TEXT,
      fundamentos TEXT,
      credito_presumido_percent REAL, reducao_base_percent REAL, diferimento TEXT,
      vigencia_inicio TEXT, vigencia_fim TEXT,
      pdf_fonte TEXT, sei_publicacao TEXT,
      confidence REAL,
      evidencias TEXT,
      raw_text_path TEXT
    );
    """)
    db.commit()
    return db

def upsert_doc(db, record: Dict[str, Any]):
    import sqlite3, json
    # doc_id = sha256 do link_pdf ou do texto
    doc_id = record.get("doc_id")
    if not doc_id:
        doc_id = sha256_bytes((record.get("pdf_fonte") or record.get("sei_publicacao") or "").encode("utf-8"))
        record["doc_id"] = doc_id

    row = (
        doc_id,
        record.get("uf"),
        record.get("fonte"),
        record.get("data_publicacao"),
        record.get("empresa"),
        record.get("cnpj"),
        record.get("programa"),
        record.get("tipo_ato"),
        record.get("nup"),
        json.dumps(record.get("fundamentos", []), ensure_ascii=False),
        record.get("icms", {}).get("credito_presumido_percent"),
        record.get("icms", {}).get("reducao_base_percent"),
        record.get("icms", {}).get("diferimento"),
        record.get("vigencia", {}).get("inicio"),
        record.get("vigencia", {}).get("fim"),
        record.get("links", {}).get("pdf_fonte"),
        record.get("links", {}).get("sei_publicacao"),
        record.get("confidence", 0),
        json.dumps(record.get("evidencias", []), ensure_ascii=False),
        record.get("raw_text_path"),
    )

    cur = db.cursor()
    cur.execute("""
    INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(doc_id) DO UPDATE SET
      uf=excluded.uf, fonte=excluded.fonte, data_publicacao=excluded.data_publicacao,
      empresa=excluded.empresa, cnpj=excluded.cnpj, programa=excluded.programa, tipo_ato=excluded.tipo_ato, nup=excluded.nup,
      fundamentos=excluded.fundamentos,
      credito_presumido_percent=excluded.credito_presumido_percent, reducao_base_percent=excluded.reducao_base_percent, diferimento=excluded.diferimento,
      vigencia_inicio=excluded.vigencia_inicio, vigencia_fim=excluded.vigencia_fim,
      pdf_fonte=excluded.pdf_fonte, sei_publicacao=excluded.sei_publicacao,
      confidence=excluded.confidence, evidencias=excluded.evidencias,
      raw_text_path=excluded.raw_text_path;
    """, row)
    db.commit()

def build_record_from_llmjson(base_fields: Dict[str, Any], llm_json: Dict[str, Any], raw_text_path: Optional[str]) -> Dict[str, Any]:
    # mistura os campos-base (uf, fonte, data_publicacao, hints) com o JSON estruturado do LLM
    record = {
        "uf": base_fields.get("uf"),
        "fonte": base_fields.get("fonte"),
        "data_publicacao": base_fields.get("data_publicacao"),
        "links": {
            "pdf_fonte": base_fields.get("pdf_fonte"),
            "sei_publicacao": base_fields.get("sei_publicacao")
        },
        "raw_text_path": str(raw_text_path) if raw_text_path else None,
        # defaults:
        "icms": {"credito_presumido_percent": None, "reducao_base_percent": None, "diferimento": None},
        "fundamentos": [], "evidencias": [], "confidence": 0.0
    }
    # sobrepõe com o que a IA retornou (apenas campos relevantes)
    for k in ("empresa","cnpj","programa","tipo_ato","nup","confidence"):
        if k in llm_json and llm_json[k] not in (None,""):
            record[k] = llm_json[k]
    if "fundamento_legal" in llm_json:
        record["fundamentos"] = llm_json["fundamento_legal"]
    if "icms" in llm_json:
        record["icms"].update(llm_json["icms"] or {})
    if "vigencia" in llm_json:
        record["vigencia"] = {
            "inicio": (llm_json["vigencia"] or {}).get("inicio"),
            "fim":    (llm_json["vigencia"] or {}).get("fim"),
        }
    if "links" in llm_json:
        record["links"].update(llm_json["links"] or {})
    if "evidencias" in llm_json:
        record["evidencias"] = llm_json["evidencias"]
    return record

def regex_fallback(text: str, base_fields: Dict[str, Any], raw_text_path: Optional[str]) -> Dict[str, Any]:
    tags = quick_tags(text)
    record = {
        "uf": base_fields.get("uf"),
        "fonte": base_fields.get("fonte"),
        "data_publicacao": base_fields.get("data_publicacao"),
        "empresa": None,
        "cnpj": ",".join(tags.get("cnpjs", [])) or None,
        "programa": base_fields.get("programa_hint"),
        "tipo_ato": None,
        "nup": ",".join(tags.get("nups", [])) or None,
        "fundamentos": [],
        "icms": {"credito_presumido_percent": None, "reducao_base_percent": None, "diferimento": None},
        "vigencia": {"inicio": None, "fim": None},
        "links": {"pdf_fonte": base_fields.get("pdf_fonte"), "sei_publicacao": base_fields.get("sei_publicacao")},
        "confidence": 0.25 if tags.get("has_icms_terms") else 0.1,
        "evidencias": [],
        "raw_text_path": str(raw_text_path) if raw_text_path else None
    }
    return record
