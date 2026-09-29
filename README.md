# ⏱️ ParouAí — Monitoramento de Tempo Parado em Roteiros

MVP do 2º Trabalho Avaliativo de **Engenharia de Software II** (PUC Minas).
Sistema que mede quanto tempo o entregador/motorista fica parado em cada ponto
do roteiro diário, guarda esse histórico e mostra tudo em um painel gerencial
com os custos do trajeto.

- **Back-end:** API REST em FastAPI (Python), persistindo em **Cloud Firestore (Firebase)**
- **Front-end:** aplicação web em Streamlit, que consome apenas a API
- **Testes:** 31 testes automatizados cobrindo RN01–RN07, RF01–RF12 e RNF01–RNF06

> A verificação requisito a requisito contra a Especificação de Requisitos está
> em [`docs/CONFORMIDADE.md`](docs/CONFORMIDADE.md). O modelo conceitual e os
> casos de uso estão em [`docs/modelo-conceitual.md`](docs/modelo-conceitual.md).

---

## Sumário

1. [Estrutura do projeto](#1-estrutura-do-projeto)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Instalação](#3-instalação)
4. [Configurando o Firebase](#4-configurando-o-firebase)
5. [Rodando o projeto](#5-rodando-o-projeto)
6. [Primeiro acesso e dados de demonstração](#6-primeiro-acesso-e-dados-de-demonstração)
7. [Passeio pelas telas](#7-passeio-pelas-telas)
8. [Rodando os testes](#8-rodando-os-testes)
9. [A API por dentro](#9-a-api-por-dentro)
10. [Problemas comuns](#10-problemas-comuns)
11. [Deploy público (Render + Streamlit Community Cloud)](#11-deploy-público-render--streamlit-community-cloud)

---

## 1. Estrutura do projeto

```
mvp-logistica-tempo-parado/
├── backend/                      # API REST (FastAPI + Firebase)
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py         # variáveis de ambiente (.env)
│   │   │   ├── firebase.py       # conexão com o Cloud Firestore
│   │   │   ├── store.py          # contrato de persistência
│   │   │   └── security.py       # login, token e perfis (RNF04)
│   │   ├── services/
│   │   │   ├── calculo.py        # RN01–RN07, RF06, RF11
│   │   │   ├── roteiros.py       # RF04, RF05
│   │   │   ├── dashboard.py      # RF07, RF08
│   │   │   ├── relatorios.py     # RF12
│   │   │   ├── parametros.py     # RF09, RF10
│   │   │   ├── auditoria.py      # RNF05
│   │   │   ├── usuarios.py       # RNF04
│   │   │   └── seed.py           # carga inicial / demonstração
│   │   ├── routers/              # endpoints HTTP
│   │   ├── repositories.py       # coleções do Firestore
│   │   ├── schemas.py            # modelo de dados (seção 8 da especificação)
│   │   └── main.py               # aplicação FastAPI
│   ├── tests/                    # 27 testes de back-end
│   └── seed.py                   # script de carga inicial
├── frontend/
│   ├── app.py                    # aplicação Streamlit
│   ├── api_client.py             # cliente HTTP da API
│   └── tests/                    # 4 testes de interface
├── docs/
│   ├── CONFORMIDADE.md           # verificação requisito a requisito
│   └── modelo-conceitual.md      # classes, casos de uso e coleções
├── main.py                       # atalho: `streamlit run main.py`
├── requirements.txt
├── .env.example                  # modelo de configuração
├── firebase.json                 # config do Firebase CLI / emulador
├── firestore.rules               # acesso direto ao banco bloqueado
└── firestore.indexes.json        # índices compostos usados pelas consultas
```

---

## 2. Pré-requisitos

| Ferramenta | Versão | Obrigatório? |
|---|---|---|
| Python | 3.11 ou superior | sim |
| pip / venv | acompanha o Python | sim |
| Conta no Firebase | plano gratuito (Spark) serve | sim, para rodar em nuvem |
| Node.js + Firebase CLI | 18+ | só para usar o emulador local |
| Java 11+ | — | só para usar o emulador local |

Confira o Python:

```bash
python3 --version
```

---

## 3. Instalação

```bash
# 1. Entre na pasta do projeto
cd mvp-logistica-tempo-parado

# 2. Crie e ative o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows (PowerShell)

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Crie o arquivo de configuração
cp .env.example .env
```

---

## 4. Configurando o Firebase

Existem **três** caminhos. Escolha um e ajuste o `.env`.

### Opção A — Firebase de verdade (recomendado para a entrega)

1. Acesse <https://console.firebase.google.com> e clique em **Adicionar projeto**.
   Dê um nome (ex.: `parouai-mvp`) e conclua o assistente.
2. No menu lateral, vá em **Criação → Firestore Database → Criar banco de dados**.
   Escolha **Modo de produção** e a região `southamerica-east1` (São Paulo).
3. Vá em **⚙️ Configurações do projeto → Contas de serviço**.
4. Clique em **Gerar nova chave privada** e confirme. Um arquivo `.json` será baixado.
5. Renomeie esse arquivo para `firebase-credentials.json` e coloque na **raiz do projeto**.
   *(Ele já está no `.gitignore` — nunca suba essa chave para o GitHub.)*
6. Edite o `.env`:

```dotenv
FIREBASE_CREDENTIALS_FILE=./firebase-credentials.json
FIREBASE_PROJECT_ID=parouai-mvp        # o ID que aparece no console
SECRET_KEY=uma-chave-aleatoria-qualquer
ADMIN_EMAIL=admin@parouai.com
ADMIN_SENHA=troque-esta-senha
```

7. (Opcional, mas recomendado) publique as regras e os índices:

```bash
npm install -g firebase-tools
firebase login
firebase use --add                     # selecione o projeto criado
firebase deploy --only firestore
```

As coleções (`motoristas`, `gerentes`, `pontos`, `roteiros`, `parametros`,
`usuarios`, `auditoria`) são criadas sozinhas no primeiro uso.

### Opção B — Emulador local do Firestore

Não precisa de conta nem de internet, mas exige Node.js e Java.

```bash
npm install -g firebase-tools
firebase emulators:start --only firestore --project demo-parouai
```

E no `.env`:

```dotenv
FIRESTORE_EMULATOR_HOST=localhost:8080
FIREBASE_PROJECT_ID=demo-parouai
```

O painel do emulador fica em <http://localhost:4000/firestore>.

### Opção C — Sem Firebase, só para dar uma olhada

```dotenv
FIRESTORE_BACKEND=memory
```

⚠️ Nesse modo **os dados somem quando a API reinicia** — serve para uma
demonstração rápida, não atende ao RNF01.

---

## 5. Rodando o projeto

São **dois terminais**, os dois com o ambiente virtual ativado.

### Terminal 1 — Back-end

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

Deve aparecer no log:

```
INFO  parouai | Iniciando ParouAí - API de Monitoramento de Tempo Parado v1.0.0
INFO  parouai | Persistência pronta. Administrador: admin@parouai.com
INFO  Uvicorn running on http://127.0.0.1:8000
```

Confira: <http://localhost:8000/health> → `{"status":"ok","persistencia":"conectada"}`
Documentação interativa: <http://localhost:8000/docs>

### Terminal 2 — Front-end

```bash
source .venv/bin/activate
streamlit run frontend/app.py
```

O navegador abre em <http://localhost:8501>.

> Se a API estiver em outro endereço, exporte antes:
> `export API_BASE_URL=http://localhost:8000`

---

## 6. Primeiro acesso e dados de demonstração

O administrador é criado automaticamente quando a API sobe, usando o que está
no `.env` (`ADMIN_EMAIL` / `ADMIN_SENHA`). O padrão é:

| Perfil | E-mail | Senha |
|---|---|---|
| Administrador | `admin@parouai.com` | `admin123` |

Para popular a base com motoristas, pontos, os roteiros A/B/C do exemplo da
especificação e ~120 dias de histórico (para o dashboard não ficar vazio):

```bash
python backend/seed.py               # com dados de demonstração
python backend/seed.py --dias 365    # histórico de um ano
python backend/seed.py --sem-demo    # só admin + parâmetros (uso real)
```

Também dá para rodar pela interface: **Administração → Dados → Executar carga
de demonstração**.

A carga cria mais dois logins:

| Perfil | E-mail | Senha |
|---|---|---|
| Gerente | `gerente@parouai.com` | `gerente123` |
| Motorista | `motorista@parouai.com` | `motorista123` |

---

## 7. Passeio pelas telas

| Tela | O que faz | Requisitos |
|---|---|---|
| **Dashboard** | Gráficos de tempo parado por dia, por mês e por período; indicadores de jornada e custo; ranking de endereços e motoristas | RF08, RF11, RN04 |
| **Registro de Ponto** | O motorista marca chegada e saída em cada ponto, na ordem do roteiro | RF05, RF06, RN01, RN02, RN06 |
| **Histórico** | Lista de paradas do período com endereço, horários e tempo parado; botão de exportar CSV | RF07, RF12 |
| **Cadastros** | Motoristas, gerentes, pontos (com coordenadas e mapa) e montagem do roteiro diário | RF01, RF02, RF03, RF04 |
| **Configurações** | Valor do combustível, custo por km, rendimento padrão, jornada, tolerância e arredondamento | RF09, RF10 |
| **Administração** | Usuários e perfis, trilha de auditoria e carga de dados | RNF04, RNF05 |

**Roteiro sugerido para a apresentação:**

1. Entre como **gerente** → *Cadastros → Roteiros* → monte um roteiro com 4 pontos.
2. Vá em *Registro de Ponto* → marque chegada e saída em cada ponto.
   Repare que o **ponto 1 aparece como "não conta"** (RN01).
3. Volte ao *Dashboard* → alterne entre **Por dia / Por mês / Por período**.
4. Em *Configurações*, mude o valor do combustível de R$ 5,85 para R$ 7,00 e
   volte ao dashboard: **o custo muda sem tocar em uma linha de código**.
5. Em *Histórico*, exporte o CSV do período.
6. Em *Administração → Auditoria*, mostre que cada marcação de horário ficou registrada.
7. Saia e entre como **motorista**: só três telas aparecem, e só os roteiros dele.

---

## 8. Rodando os testes

```bash
source .venv/bin/activate
pytest -q
```

Saída esperada:

```
31 passed
```

Os testes sobem a API inteira com persistência em memória, então **não mexem no
seu Firebase**. Eles cobrem:

- `backend/tests/test_regras_negocio.py` — RN01 a RN07 (inclusive o exemplo
  A da especificação: 15 + 10 + 50 = 75 min)
- `backend/tests/test_requisitos_funcionais.py` — RF01 a RF12
- `backend/tests/test_nao_funcionais.py` — persistência, perfis, auditoria,
  LGPD e o limite de 3 s do dashboard com 12 meses de dados
- `frontend/tests/test_app.py` — a interface abre todas as telas sem erro e
  respeita os perfis

Para ver apenas um grupo:

```bash
pytest backend/tests/test_regras_negocio.py -v
```

---

## 9. A API por dentro

Toda rota (exceto `/`, `/health` e `/auth/login`) exige o cabeçalho
`Authorization: Bearer <token>`.

| Método | Rota | O que faz | Perfis |
|---|---|---|---|
| POST | `/auth/login` | Autentica e devolve o token | — |
| GET | `/auth/me` | Dados do usuário logado | todos |
| GET/POST/PUT/DELETE | `/motoristas` | RF01 | leitura: todos · escrita: gestão |
| GET/POST/PUT/DELETE | `/gerentes` | RF02 | leitura: todos · escrita: gestão |
| GET/POST/PUT/DELETE | `/pontos` | RF03 | leitura: todos · escrita: gestão |
| GET/POST/PUT/DELETE | `/roteiros` | RF04 | leitura: todos · escrita: gestão |
| POST | `/roteiros/{id}/pontos/{ordem}/chegada` | RF05 | todos |
| POST | `/roteiros/{id}/pontos/{ordem}/saida` | RF05 | todos |
| GET | `/historico` | RF07 | todos |
| GET | `/dashboard` | RF08 | todos |
| GET/PUT | `/parametros` | RF09, RF10 | leitura: todos · escrita: gestão |
| GET | `/relatorios/historico.csv` | RF12 | todos |
| GET | `/relatorios/completo` | RF12 | todos |
| GET | `/auditoria` | RNF05 | gestão |
| GET/POST/PUT/DELETE | `/usuarios` | RNF04 | administrador |
| POST | `/admin/seed` | Carga de demonstração | administrador |

Exemplo pelo terminal:

```bash
# login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@parouai.com","senha":"admin123"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# tempo parado por mês nos últimos 12 meses
curl -s "http://localhost:8000/dashboard?agrupamento=mes" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Toda resposta traz o cabeçalho `X-Tempo-Resposta-ms`, útil para conferir o
limite de 3 segundos do RNF03.

---

## 10. Problemas comuns

**`RuntimeError: Nenhuma credencial do Firebase configurada`**
O `.env` não foi criado ou não aponta para o JSON. Confira se o arquivo
`firebase-credentials.json` está na raiz e se `FIREBASE_CREDENTIALS_FILE`
tem o caminho certo.

**`Não foi possível falar com a API em http://localhost:8000`** (no Streamlit)
O back-end não está rodando. Volte ao Terminal 1 e suba o uvicorn.

**`403 PERMISSION_DENIED` do Firestore**
O Firestore não foi criado no console (passo 2 da Opção A) ou a service account
é de outro projeto. Confira o `FIREBASE_PROJECT_ID`.

**`The query requires an index`**
Consulta composta sem índice. Rode `firebase deploy --only firestore:indexes`
ou clique no link que aparece na mensagem de erro do Firestore.

**`ModuleNotFoundError: No module named 'app'`**
O uvicorn precisa do `--app-dir backend`. Use o comando exatamente como está
na seção 5.

**A porta 8000 ou 8501 já está em uso**
`uvicorn ... --port 8001` e `streamlit run frontend/app.py --server.port 8502`
(nesse caso exporte `API_BASE_URL=http://localhost:8001`).

**O dashboard aparece vazio**
Ainda não há roteiros no período. Rode `python backend/seed.py` ou amplie as
datas no filtro.

---

## 11. Deploy público (Render + Streamlit Community Cloud)

Isso publica o sistema em dois links fixos, acessíveis por qualquer pessoa,
sem depender do seu computador ligado. Nenhum dos dois serviços pede cartão de
crédito no plano gratuito usado aqui.

| Camada | Serviço | Custo |
|---|---|---|
| Back-end (API) | [Render](https://render.com) — Web Service, plano Free | R$ 0 (750h/mês grátis; "dorme" após 15 min sem uso) |
| Front-end (Streamlit) | [Streamlit Community Cloud](https://share.streamlit.io) | R$ 0 (sempre grátis para apps públicos) |
| Banco de dados | Cloud Firestore | já configurado na seção 4 |

O código precisa estar em um repositório do GitHub — os dois serviços fazem
o deploy direto de lá. Se você ainda não deu `push` da branch com este
projeto, faça isso antes de começar.

### 11.1 Back-end no Render

1. Acesse <https://dashboard.render.com> e entre com sua conta do GitHub
2. Clique em **New +** → **Blueprint**
3. Selecione o repositório e a branch deste projeto — o Render encontra
   sozinho o arquivo `render.yaml` na raiz e preenche a maior parte da
   configuração (nome, comando de build, comando de start, plano Free)
4. Antes de confirmar, o Render pede os valores marcados como secretos no
   blueprint. Preencha:

   | Campo | Valor |
   |---|---|
   | `FIREBASE_CREDENTIALS_JSON` | abra o `firebase-credentials.json` da raiz do projeto e cole **o conteúdo inteiro** do arquivo |
   | `ADMIN_SENHA` | uma senha forte — **não use `admin123` aqui**, esse link fica público |

   (`FIREBASE_PROJECT_ID`, `CORS_ORIGINS` e `SECRET_KEY` já vêm preenchidos —
   o `SECRET_KEY` é gerado aleatoriamente pelo próprio Render.)
5. Clique em **Apply** / **Create Web Service** e aguarde o build (2–4 min)
6. Quando o status virar **Live**, copie a URL do serviço — algo como
   `https://parouai-backend.onrender.com`
7. Confirme que funcionou: abra `https://SUA-URL.onrender.com/health` no
   navegador. Deve responder `{"status":"ok","persistencia":"conectada"}`

> A primeira requisição depois de 15 minutos parado demora ~30-50s (o Render
> "acorda" o serviço). É normal — só acontece na primeira chamada.

### 11.2 Front-end no Streamlit Community Cloud

1. Acesse <https://share.streamlit.io> e entre com sua conta do GitHub
2. Clique em **Create app** → **From existing repo**
3. Preencha:

   | Campo | Valor |
   |---|---|
   | Repository | o mesmo repositório do projeto |
   | Branch | a branch deste projeto |
   | Main file path | `frontend/app.py` |

4. Antes de publicar, clique em **Advanced settings** → **Secrets** e cole:

   ```toml
   API_BASE_URL = "https://SUA-URL-DO-RENDER.onrender.com"
   ```

   (a URL copiada no passo 11.1.6, sem a barra `/` no final)

5. Clique em **Deploy**. Em 1–2 minutos o app abre em uma URL como
   `https://SEU-APP.streamlit.app`

### 11.3 Testando o link público

1. Abra a URL do Streamlit
2. Entre com `admin@parouai.com` e a senha que você definiu no passo 11.1.4
3. Rode a carga de demonstração em **Administração → Dados**, se a base
   estiver vazia
4. Pronto — esse link funciona para qualquer pessoa, a qualquer hora, sem
   você precisar rodar nada localmente

### Mantendo os dois deploys atualizados

Ambos os serviços re-fazem o deploy sozinhos a cada `push` na branch
configurada. Depois de qualquer alteração no código:

```bash
git add .
git commit -m "sua mensagem"
git push
```

O Render e o Streamlit Cloud detectam o novo commit e publicam a versão nova
automaticamente — não precisa repetir os passos acima.

---

## Nome do produto

**ParouAí** — o nome nasce da pergunta que o gestor faz hoje sem ter resposta:
*"parou aí por quê, e por quanto tempo?"*. É a sugestão do time para os pontos
extras da atividade; trocar o nome exige mexer só no `.env` (`APP_NAME`) e no
título do front-end.

---

Projeto acadêmico · Engenharia de Software II · PUC Minas
