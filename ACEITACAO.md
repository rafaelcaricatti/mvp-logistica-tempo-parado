# Testes de aceitação — ParouAí

Testes ponta a ponta com **Playwright**, rodando no navegador (Chromium) contra o app de verdade:
back-end FastAPI (base em memória, sem Firebase) + front-end Streamlit. O próprio Playwright liga
os dois servidores (`webServer` em `playwright.config.js`), roda os testes e desliga tudo.

## Como executar

```bash
git clone https://github.com/rafaelcaricatti/mvp-logistica-tempo-parado.git
cd mvp-logistica-tempo-parado
npm install            # baixa o Chromium e cria o .venv com as dependências Python
npx playwright test    # roda os 3 testes e gera o relatório HTML
npx playwright show-report   # (opcional) abre o relatório em playwright-report/index.html
```

Pré-requisitos: Node 18+ e Python 3.11+.

Resultado da última execução: **3 passed (9.8s)**, bem abaixo do limite de 30 s. Nenhum arquivo usa
`waitForTimeout`: toda espera é feita pelas asserções do próprio Playwright (`expect(...).toBeVisible()`
e similares), que esperam o elemento aparecer. Os localizadores são `getByRole`, `getByLabel` e `getByText`.

## Mapa dos testes

| # | Critério (Dado / Quando / Então) | Arquivo / linha | O que prova |
|---|---|---|---|
| 1 | **Caminho principal.** **Dado** que entrei como administrador, **quando** cadastro um motorista, monto um roteiro de 2 pontos para ele e registro chegada e saída em cada ponto, na ordem, **então** vejo "Roteiro criado com 2 pontos", o ponto de partida marcado como "não conta tempo parado" e "Todos os pontos do roteiro foram concluídos." | `tests/roteiro.spec.js:13` | O fluxo mais importante do sistema funciona de ponta a ponta: cadastro (RF01), montagem de roteiro (RF04) e registro de chegada/saída (RF05). O ponto de partida não entra no tempo parado (RN01). |
| 2 | **Regra de erro.** **Dado** que existe um motorista cadastrado, **quando** tento gerar um roteiro com apenas 1 endereço, **então** vejo o aviso "Informe pelo menos dois pontos (partida + uma parada)." e nenhum roteiro é criado para o motorista. | `tests/roteiro.spec.js:45` | O sistema barra um roteiro inválido (RF04 / RN06). Não basta o aviso aparecer: o teste confere na tela de Registro de Ponto que nada foi gravado. |
| 3 | **Regra de estado.** **Dado** que um motorista tem um roteiro de 3 pontos, já saiu do ponto 1 e registrou a chegada no ponto 2, **quando** recarrego a página e entro de novo no sistema, **então** o roteiro continua no ponto 2 com a chegada já registrada: aparece "Registrar saída" e não aparece mais "Registrar chegada". | `tests/estado.spec.js:14` | As marcações ficam gravadas no servidor, não na tela. O teste confirma que recarregar realmente apagou a sessão do navegador (o login volta a aparecer) e, mesmo assim, o andamento do roteiro continua igual. |

Arquivos de apoio: `tests/ajuda.js` (passos de preparação: login, navegação, cadastro, montar roteiro),
`playwright.config.js` (servidores, tempo limite e relatório), `scripts/preparar.js` (rodado pelo `npm install`).

## Anti-teste (prova de que o teste 3 detecta o defeito)

Para garantir que o teste 3 não passa "à toa", o app foi quebrado de propósito e o teste rodou contra ele.

**Defeito introduzido** (em `frontend/app.py`, página Registro de Ponto): os botões "Registrar chegada"
e "Registrar saída" passaram a guardar o horário só em `st.session_state` (memória da sessão do
navegador), sem chamar a API. Na tela tudo parece funcionar, porque os pontos avançam normalmente, mas nada
chega ao servidor.

**Resultado com o defeito: o teste ficou vermelho, e no ponto certo.** Todos os passos antes de recarregar
passaram (a tela avançou para o ponto 2). A falha veio logo depois do recarregamento:

```
✘ tests/estado.spec.js:14:1 › o andamento do roteiro continua igual depois de recarregar a página

  Error: expect(locator).toBeVisible() failed
  Locator: getByRole('heading', { name: /Ponto 2: Rua B, 2/ })
  Expected: visible
  Error: element(s) not found

  > 37 |   await expect(page.getByRole('heading', { name: /Ponto 2: Rua B, 2/ })).toBeVisible()
```

Ou seja: depois de recarregar, o roteiro tinha voltado ao ponto 1, porque o andamento estava só na sessão
que foi perdida.

**Conserto:** o defeito foi desfeito (`git checkout frontend/app.py`) e a suíte voltou a ficar verde:
3 passed.

## Observações

- **Os testes rodam um de cada vez (`workers: 1`).** Em paralelo eles falhavam de forma intermitente. A
  lista de motoristas do front-end usa `st.cache_data`, que é compartilhado entre todas as sessões. Assim,
  quando um teste cadastrava um motorista, a lista mudava na tela do outro, e o Streamlit reiniciava a caixa
  "Motorista" no meio do teste. Em série a suíte leva cerca de 10 s. (No app real isso também pode
  acontecer com dois gestores usando o sistema ao mesmo tempo.)
- **A caixa de seleção é preenchida digitando.** O Streamlit só desenha cerca de 10 opções da lista por vez.
  Com mais motoristas na base, clicar direto na opção falhava, porque ela nem estava na página. O passo
  `escolher` (`tests/ajuda.js`) digita o nome para filtrar e depois clica.
- Estabilidade conferida rodando a suíte 8 vezes seguidas (`--repeat-each=8`): 24 de 24 passaram.
