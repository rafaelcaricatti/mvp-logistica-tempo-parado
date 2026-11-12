// Passos de preparação compartilhados pelos testes de aceitação.
// Não é um teste (o nome não termina em .spec.js): só faz o que o usuário faria
// para chegar a um ponto de partida. Quem afirma é sempre o teste.
const { expect } = require('@playwright/test')

// A base do app em teste é em memória e COMPARTILHADA entre os testes. Por isso
// cada teste cria seus próprios dados, com nome único, e nunca depende de a base
// estar vazia ou do que outro teste deixou lá.
function nomeUnico(prefixo) {
  return `${prefixo} ${Date.now().toString(36)}${Math.floor(Math.random() * 1000)}`
}

// O app recusa dois motoristas com o mesmo documento, então ele também é único.
function documentoUnico() {
  return `${Date.now()}${Math.floor(Math.random() * 1000)}`
}

// Dado que entrei no sistema como administrador (conta padrão do app).
async function entrarComoAdmin(page) {
  await page.goto('/')
  await page.getByLabel('E-mail').fill('admin@parouai.com')
  await page.getByLabel('Senha', { exact: true }).fill('admin123')
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('heading', { name: 'Dashboard Gerencial' })).toBeVisible()
}

// Vai para uma tela pelo menu lateral ("Cadastros", "Registro de Ponto"...).
async function irPara(page, tela) {
  await page.getByRole('radiogroup', { name: 'Navegação' }).getByText(tela, { exact: true }).click()
  await expect(page.getByRole('heading', { name: tela, level: 1 })).toBeVisible()
}

// Cadastra um motorista pela tela de Cadastros e confirma o aviso de sucesso.
async function cadastrarMotorista(page, nome) {
  await irPara(page, 'Cadastros')
  const aba = page.getByRole('tabpanel', { name: 'Motoristas (RF01)' })
  await aba.getByLabel('Nome completo').fill(nome)
  await aba.getByLabel('Documento (CPF/CNH)').fill(documentoUnico())
  await aba.getByLabel('Telefone', { exact: true }).fill('31999990000')
  await aba.getByLabel('Veículo', { exact: true }).fill('Fiorino')
  await aba.getByRole('button', { name: 'Salvar motorista' }).click()
  await expect(page.getByText('Motorista cadastrado.')).toBeVisible()
}

// Escolhe uma opção em uma caixa de seleção do Streamlit: abre a lista, digita
// para filtrar e clica. Digitar é necessário porque o Streamlit só desenha umas
// 10 opções por vez — com mais motoristas na base, a opção nem estaria na página.
async function escolher(page, rotulo, opcao) {
  const caixa = page.getByRole('combobox', { name: rotulo })
  await caixa.click()
  await caixa.fill(opcao)
  await page.getByRole('option', { name: opcao }).click()
}

// Monta, pela aba Roteiros, um roteiro com os endereços dados (um por linha).
async function montarRoteiro(page, motorista, enderecos) {
  const roteiros = page.getByRole('tabpanel', { name: 'Roteiros (RF04)' })
  await page.getByRole('tab', { name: 'Roteiros (RF04)' }).click()
  await escolher(page, 'Motorista responsável', motorista)
  await roteiros.getByLabel('Endereços avulsos').fill(enderecos.join('\n'))
  await roteiros.getByRole('button', { name: 'Gerar roteiro' }).click()
  await expect(page.getByText(`Roteiro criado com ${enderecos.length} pontos`)).toBeVisible()
}

module.exports = { nomeUnico, entrarComoAdmin, irPara, cadastrarMotorista, escolher, montarRoteiro }
