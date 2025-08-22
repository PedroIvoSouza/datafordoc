# -*- coding: utf-8 -*-
import os, json
from typing import Optional, Dict, Any
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Usando SDK oficial v1
try:
    from openai import OpenAI
    _client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except Exception:
    _client = None

# JSON Schema para saída estruturada
SCHEMA = {
  "type": "json_schema",
  "json_schema": {
    "name": "AtoFiscal",
    "schema": {
      "type": "object",
      "properties": {
        "uf": { "type": ["string","null"] },
        "fonte": { "type": ["string","null"] },
        "data_publicacao": { "type": ["string","null"] },
        "empresa": { "type": ["string","null"] },
        "cnpj": { "type": ["string","null"] },
        "programa": { "type": ["string","null"] },
        "tipo_ato": { "type": ["string","null"] },
        "nup": { "type": ["string","null"] },
        "fundamento_legal": { "type": "array", "items": { "type": "string" } },
        "icms": {
          "type": "object",
          "properties": {
            "credito_presumido_percent": { "type": ["number","null"] },
            "reducao_base_percent": { "type": ["number","null"] },
            "diferimento": { "type": ["string","null"] }
          },
          "required": ["credito_presumido_percent", "reducao_base_percent", "diferimento"],
          "additionalProperties": False
        },
        "vigencia": {
          "type": "object",
          "properties": {
            "inicio": { "type": ["string","null"] },
            "fim": { "type": ["string","null"] }
          },
          "required": ["inicio", "fim"],
          "additionalProperties": False
        },
        "links": {
          "type": "object",
          "properties": {
            "pdf_fonte": { "type": ["string","null"] },
            "sei_publicacao": { "type": ["string","null"] }
          },
          "required": ["pdf_fonte", "sei_publicacao"],
          "additionalProperties": False
        },
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
        "evidencias": { "type": "array", "items": { "type": "string" } }
      },
      "required": ["confidence"],
      "additionalProperties": False
    },
    "strict": True
  }
}

def extract_structured(texto: str,
                       uf: str,
                       fonte: str,
                       data_publicacao: str,
                       pdf_fonte: Optional[str],
                       sei_publicacao: Optional[str],
                       programa_hint: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Retorna um dicionário respeitando o SCHEMA.
    Se não houver OPENAI_API_KEY configurada, retorna None.
    """
    if not _client:
        return None

    system = "Você extrai informações de atos de incentivos fiscais a partir de DOEs e publicações do SEI."
    user = f"""
Extraia apenas o que estiver explícito no texto. Se não houver, use null.
Campos: programa, tipo_ato, empresa, cnpj, nup, fundamento_legal[],
icms{{credito_presumido_percent, reducao_base_percent, diferimento}},
vigencia{{inicio,fim}}, links{{pdf_fonte, sei_publicacao}} e confidence (0..1).

Contexto fixo: uf={uf}, fonte={fonte}, data_publicacao={data_publicacao},
pdf_fonte={pdf_fonte or "null"}, sei_publicacao={sei_publicacao or "null"},
programa_hint={programa_hint or "null"}.
Texto:
\"\"\"
{texto[:12000]}
\"\"\"
"""

    try:
        r = _client.responses.create(
            model=OPENAI_MODEL,
            input=[{"role":"system","content":system},
                   {"role":"user","content":user}],
            response_format=SCHEMA,
            temperature=0.0,
        )
        # SDK v1: conteúdo estruturado vem como texto JSON
        content = r.output[0].content[0].text  # type: ignore
        return json.loads(content)
    except Exception as e:
        print("[LLM] Erro:", e)
        return None
