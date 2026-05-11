# Challenge Núclea · FIAP — RAIZ (FIDC)

Repositório da solução entregue à **Núclea** no Challenge proposto em **08/2025** para as turmas de graduação da FIAP no curso de **Data Science**.

Aplicação web (**Streamlit**) para análise de FIDC: dashboard operacional, documentos (PDF), chatbot com documentos via Gemini, precificação com modelo de ML (`fidc_model_v2.py`) e autenticação por usuários definidos em arquivo YAML.

---

## Visão geral da arquitetura

| Camada | Responsabilidade |
|--------|------------------|
| **`app.py`** | Ponto de entrada Streamlit: login, tema, navegação e processamento de XMLs pendentes ao iniciar. |
| **`pages/`** | Páginas multipágina: dashboard (`01_dashboard.py`), documentos (`02_documentos`), precificação (`03_precificacao`). |
| **`components/`** | UI reutilizável: sidebar, gráficos Plotly, cards e filtros. |
| **`core/`** | Lógica independente da interface: auth (`users.yaml`), extração XML (`extractor.py`), pipeline inbox → cache (`processor.py`), leitura para o dashboard (`loader.py`), métricas (`metrics.py`). |
| **`config/`** | `funds.yaml` (fundos e CNPJs), `settings.yaml` (ajustes gerais). **`users.yaml` não versionado** — criado localmente (ver tutorial). |
| **`data/funds/<id>/`** | Por fundo: `informes/inbox` (XMLs novos), `processed`, `cache` (JSON extraído), `documentos/` (PDFs por tipo), `insights/`. Pastas de dados sensíveis ou geradas costumam estar no `.gitignore`. |
| **`fidc_model_v2.py`** | Script de treino/avaliação do modelo de precificação (scikit-learn, joblib). |
| **`manage_users.py`** | CLI para criar `config/users.yaml`, listar usuários e resetar senha. |
| **`setup_structure.py`** | Gera esqueleto de pastas/arquivos (uso histórico de bootstrap; o repositório já contém a estrutura principal). |
| **`tests/`** | Testes automatizados (executar com `python -m unittest`, conforme abaixo). |

Fluxo resumido dos informes: XML em **`informes/inbox/`** → processamento → JSON em **`informes/cache/`** e XML em **`informes/processed/`** — refletido no dashboard após login.

---

## Pré-requisitos

- **Python 3.10+** (recomendado 3.11 ou 3.12)
- **pip** (ou ambiente virtual com pip)
- Navegador moderno (Chrome, Edge ou Firefox)

No Windows, use **PowerShell** ou **Prompt de Comando** na pasta do repositório.

---

## Tutorial: rodar o projeto

### 1. Clonar e entrar na pasta

```bash
git clone <url-do-repositorio>
cd Challenge-Nuclea-FIAP
```

### 2. Ambiente virtual (recomendado)

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Usuários de login

O arquivo `config/users.yaml` **não está no Git** (credenciais). Gere-o na primeira execução:

```bash
python manage_users.py init
```

Isso cria um usuário **admin** com senha inicial **admin123**. Para produção ou avaliação, altere com:

```bash
python manage_users.py resetar
```

Outros comandos: `python manage_users.py listar`, `python manage_users.py criar`.

### 4. Configurar a chave da API Gemini para o chatbot

O chatbot de documentos só funciona se houver uma chave válida da API Gemini configurada localmente. Crie a pasta `.streamlit` na raiz do projeto, caso ela ainda não exista, e adicione o arquivo `.streamlit/secrets.toml` com o conteúdo abaixo:

```toml
GEMINI_API_KEY = "sua_chave_aqui"
```

Sem essa configuração, a aplicação pode ser iniciada normalmente, mas a funcionalidade de chatbot ficará indisponível.

Importante: esse arquivo deve permanecer apenas no ambiente local e não deve ser versionado no Git.

### 5. Subir a aplicação Streamlit

**Opção A — script na raiz**

```bash
python run_app.py
```

**Opção B — comando direto**

```bash
python -m streamlit run app.py
```

O terminal exibirá uma URL local (em geral `http://localhost:8501`). Abra no navegador e faça login.

### 6. Dados de exemplo (opcional)

Para o dashboard e o processamento exibirem conteúdo, coloque arquivos **XML** de informe nas pastas `data/funds/<id>/informes/inbox/` conforme os IDs definidos em `config/funds.yaml` (por exemplo `xama`). PDFs de documentos seguem a estrutura sob `data/funds/<id>/documentos/`, conforme a página **Documentos** da aplicação.

---

## Dependências principais

Definidas em `requirements.txt`:

- **streamlit** — interface web
- **pandas**, **numpy** — dados e cálculos
- **plotly** — gráficos interativos
- **scikit-learn**, **joblib** — modelo de ML e persistência
- **pdfplumber** — leitura de PDFs no módulo de documentos
- **pyyaml** — `funds.yaml`, `settings.yaml`, `users.yaml`
- **bcrypt** — hash de senhas em `users.yaml`

---

## Testes

A pasta **`tests/`** está preparada para testes com **`unittest`**. Quando houver casos implementados em `test_*.py`, execute:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## Modelo de precificação

O arquivo **`fidc_model_v2.py`** treina e avalia o classificador de pools; pode ser executado diretamente quando houver dados e caminhos configurados no próprio script:

```bash
python fidc_model_v2.py
```

Consulte as constantes e caminhos no início do arquivo para adaptar ao seu ambiente.

---

## Estrutura de pastas (referência rápida)

```
Challenge-Nuclea-FIAP/
├── app.py                 # Entrada Streamlit
├── run_app.py             # Atalho: streamlit run app.py
├── fidc_model_v2.py       # ML precificação
├── manage_users.py        # Gestão de usuários
├── setup_structure.py     # Bootstrap de estrutura (opcional)
├── requirements.txt
├── config/
│   ├── funds.yaml
│   ├── settings.yaml
│   └── users.yaml         # local apenas (gitignored)
├── core/                  # Negócio e ingestão
├── components/            # UI compartilhada
├── pages/                 # Páginas Streamlit
├── data/funds/            # Dados por fundo (parcialmente ignorados pelo git)
└── tests/
```

---

## Licença e uso acadêmico

Este repositório foi produzido no contexto do challenge FIAP/Núclea. Use conforme as regras da instituição e do trabalho entregue.
