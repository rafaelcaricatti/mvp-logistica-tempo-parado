// Roda sozinho no fim do `npm install` (script "postinstall" do package.json).
// Deixa tudo pronto para `npx playwright test` funcionar sem nenhum passo manual:
//   1. baixa o navegador Chromium usado pelo Playwright;
//   2. cria o ambiente virtual do app (.venv) e instala as dependências Python.
const { spawnSync } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const raiz = path.join(__dirname, '..')
const windows = process.platform === 'win32'
const pythonDoVenv = path.join(raiz, '.venv', windows ? 'Scripts/python.exe' : 'bin/python')

function rodar(comando, args) {
  return spawnSync(comando, args, { cwd: raiz, stdio: 'inherit' })
}

function falhar(mensagem) {
  console.error(`\n[preparar] ${mensagem}\n`)
  process.exit(1)
}

// 1. Navegador do Playwright (chama o CLI do pacote direto, sem passar por shell)
console.log('[preparar] Baixando o Chromium do Playwright...')
const cliDoPlaywright = require.resolve('@playwright/test/cli')
if (rodar(process.execPath, [cliDoPlaywright, 'install', 'chromium']).status !== 0) {
  falhar('Não consegui baixar o Chromium. Rode `npx playwright install chromium` e tente de novo.')
}

// 2. Ambiente Python do app
if (!fs.existsSync(pythonDoVenv)) {
  const candidatos = windows ? ['python', 'py', 'python3'] : ['python3', 'python']
  const python = candidatos.find((c) => spawnSync(c, ['--version']).status === 0)
  if (!python) falhar('Python 3.11+ não encontrado. Instale o Python e rode `npm install` de novo.')
  console.log(`[preparar] Criando o ambiente virtual (.venv) com ${python}...`)
  if (rodar(python, ['-m', 'venv', '.venv']).status !== 0) falhar('Não consegui criar o .venv.')
}

console.log('[preparar] Instalando as dependências Python (pode levar alguns minutos)...')
if (rodar(pythonDoVenv, ['-m', 'pip', 'install', '--quiet', '-r', 'requirements.txt']).status !== 0) {
  falhar('Falha ao instalar as dependências Python (requirements.txt).')
}
console.log('[preparar] Pronto.')
