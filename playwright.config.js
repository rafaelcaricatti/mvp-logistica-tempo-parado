// playwright.config.js
const { defineConfig, devices } = require('@playwright/test')

// Portas incomuns de propósito: não colidem com um app que a pessoa já
// tenha ligado à mão nas portas padrão (8000 e 8501).
const PORTA_API = 8100
const PORTA_TELA = 8601

// Python do ambiente virtual criado pelo `npm install` (scripts/preparar.js).
const PYTHON = process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python'

module.exports = defineConfig({
  testDir: './tests',
  timeout: 30_000,
  // Um teste por vez. A base em memória e o cache de motoristas do Streamlit
  // (st.cache_data) são compartilhados entre sessões: em paralelo, um teste que
  // cadastra um motorista muda a lista do outro e o Streamlit reinicia a caixa
  // "Motorista" no meio do teste. Em série a suíte toda leva ~10 s.
  workers: 1,
  fullyParallel: false,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: `http://127.0.0.1:${PORTA_TELA}`, trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],

  // O Playwright liga o back-end e o front-end, espera os dois responderem,
  // roda os testes e desliga tudo. Nenhum passo manual.
  webServer: [
    {
      // Back-end (FastAPI). Persistência em memória: nenhum Firebase é tocado
      // e cada execução começa com a base limpa (só o administrador padrão).
      command: `"${PYTHON}" -m uvicorn app.main:app --host 127.0.0.1 --port ${PORTA_API} --app-dir backend`,
      url: `http://127.0.0.1:${PORTA_API}/health`,
      env: { FIRESTORE_BACKEND: 'memory' },
      reuseExistingServer: false,
      timeout: 60_000
    },
    {
      // Front-end (Streamlit), apontando para o back-end acima.
      command:
        `"${PYTHON}" -m streamlit run frontend/app.py --server.address 127.0.0.1 ` +
        `--server.port ${PORTA_TELA} --server.headless true --browser.gatherUsageStats false`,
      url: `http://127.0.0.1:${PORTA_TELA}/_stcore/health`,
      env: { API_BASE_URL: `http://127.0.0.1:${PORTA_API}` },
      reuseExistingServer: false,
      timeout: 90_000
    }
  ]
})
