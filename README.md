# IA DOE→SEI (Starter Kit)

Este kit implementa **um pipeline simples** para:
1) Baixar páginas ou PDFs (DOE ou página pública do SEI);
2) Extrair texto;
3) Enriquecer com IA (OpenAI) usando **JSON estruturado**;
4) Salvar tudo em **SQLite** e exportar CSV.

> Foco inicial: facilidade — sem Docker, sem Postgres. Tudo roda em Python puro.
> Depois você pode escalar conforme precisar.

---

## 🚀 Passo a passo (bem mastigado)

### 0) Pré-requisitos
- Ter **Python 3.10+** instalado (no Windows/Mac/Linux).
- Ter uma **chave da OpenAI** (ex.: `sk-...`).

### 1) Baixe este pacote
Você já está com a pasta após extrair o `.zip`. (Se não, baixe o arquivo `.zip` que eu te enviei neste chat e extraia).

### 2) Instale as dependências
No terminal, entre na pasta e rode:

```bash
# (opcional) criar um ambiente virtual
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3) Configure sua chave da OpenAI
Copie o `.env.example` para `.env` e edite a variável:

```bash
cp .env.example .env
# Abra o arquivo .env e cole sua OPENAI_API_KEY
```

### 4) Informe as fontes públicas a coletar
Edite `seeds.csv` com as **linhas que você quer processar**. Cada linha é uma fonte (um PDF do DOE, uma página HTML pública do DOE, ou o PDF da publicação eletrônica do SEI).

- Colunas do `seeds.csv`:
  - `uf` (ex.: AL, CE, PE...)
  - `fonte` (valores aceitos: `DOE_PDF`, `DOE_HTML`, `SEI_PUB_PDF`)
  - `url` (link público do PDF ou página — comece com poucos para testar)
  - `data_publicacao` (formato ISO: YYYY-MM-DD)
  - `programa_hint` (opcional — ex.: PCA, PRODEPE, FDI, etc. Ajuda a IA a acertar o programa)

Exemplo (já existe um `seeds.csv` com exemplos de placeholders).

### 5) Execute a coleta e extração
```bash
python run.py seeds.csv
```

- Saída:
  - Banco **SQLite** em: `data/outputs/docs.sqlite3`
  - Textos/arquivos baixados em: `data/inputs/`
  - Log amigável no terminal

### 6) Exporte para CSV (para analisar no Excel/planilha)
```bash
python export_csv.py
```
Gera `data/outputs/atos.csv` com os campos principais.

### 7) Rotina diária (opcional)
Crie um agendamento (cron) para rodar todo dia às 08:00 (horário de Recife):
```bash
# abra o crontab
crontab -e
# adicione a linha (ajuste o caminho para a sua pasta):
0 8 * * * cd /CAMINHO/ia-doe-sei-starter && . .venv/bin/activate && python run.py seeds.csv >> run.log 2>&1
```

---

## ❓ Dúvidas comuns

- **“Não tenho links prontos do DOE”**: comece copiando **1 ou 2 PDFs públicos** (ou páginas HTML) de diários oficiais que você já conhece. Depois incrementamos com buscadores por UF.
- **“E o SEI?”**: este starter aceita também `SEI_PUB_PDF` (o PDF da **Publicação Eletrônica**, que é pública). Cole o link direto da publicação quando tiver. Em seguida, a IA extrai os campos e o pipeline salva igual a um DOE.
- **“Sem chave OpenAI?”**: o script roda com **fallback por regex**, guardando o texto bruto e tentando capturar **CNPJ** e **NUP**. A IA deixa tudo mais completo, mas não é obrigatória.
- **“OCR?”**: se o PDF do DOE for imagem, você precisará de OCR (ex.: `tesseract`). Para começar simples, teste com PDFs pesquisáveis.

---

## 📦 Estrutura da pasta

```
ia-doe-sei-starter/
  data/
    inputs/    # PDFs/HTML baixados
    outputs/   # SQLite e CSVs
  src/
    run_utils.py      # funções utilitárias (download, extração, regex)
    llm_extract.py    # chamada à OpenAI com JSON estruturado
  run.py              # orquestra a execução com base no seeds.csv
  export_csv.py       # exporta do SQLite para CSV
  seeds.csv           # suas fontes públicas
  requirements.txt
  .env.example
  README.md
```

---

## 🧪 Primeiro teste
1) Deixe **1 linha** no `seeds.csv` (um PDF ou HTML público que contenha termos como “incentivo fiscal”, “crédito presumido”, etc.).  
2) Rode `python run.py seeds.csv`.  
3) Em caso de erro, me diga o que apareceu. Vamos ajustar juntos.

Boa captura! 💪
