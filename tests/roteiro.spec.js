// Testes de aceitação do ParouAí — cenários 1 (caminho principal) e 2 (regra
// que barra erro). Regras de negócio: RN01 (a partida não conta tempo parado),
// RN06 (pontos em ordem sequencial) e RF04/RF05 (montar roteiro e registrar ponto).
const { test, expect } = require('@playwright/test')
const { nomeUnico, entrarComoAdmin, irPara, cadastrarMotorista, escolher } = require('./ajuda')

// C1 · Caminho principal — do cadastro ao roteiro concluído
//   Dado que entrei como administrador
//   Quando cadastro um motorista, monto um roteiro de 2 pontos para ele e registro
//          chegada e saída em cada ponto, na ordem
//   Então vejo "Roteiro criado com 2 pontos", o ponto de partida marcado como
//          "não conta tempo parado" e "Todos os pontos do roteiro foram concluídos."
test('monta um roteiro e registra chegada e saída em todos os pontos', async ({ page }) => {
  const motorista = nomeUnico('Motorista')
  await entrarComoAdmin(page)
  await cadastrarMotorista(page, motorista)

  const roteiros = page.getByRole('tabpanel', { name: 'Roteiros (RF04)' })
  await page.getByRole('tab', { name: 'Roteiros (RF04)' }).click()
  await escolher(page, 'Motorista responsável', motorista)
  await roteiros.getByLabel('Endereços avulsos').fill('Rua da Partida, 100\nRua da Parada, 200')
  await roteiros.getByRole('button', { name: 'Gerar roteiro' }).click()
  await expect(page.getByText(/Roteiro criado com 2 pontos/)).toBeVisible()

  await irPara(page, 'Registro de Ponto')
  await escolher(page, 'Motorista', motorista)

  const partida = page.getByRole('heading', { name: /Ponto 1: Rua da Partida, 100/ })
  await expect(partida).toContainText('ponto de partida — não conta tempo parado')
  await page.getByRole('button', { name: 'Registrar chegada' }).click()
  await page.getByRole('button', { name: 'Registrar saída' }).click()

  await expect(page.getByRole('heading', { name: /Ponto 2: Rua da Parada, 200/ })).toBeVisible()
  await page.getByRole('button', { name: 'Registrar chegada' }).click()
  await page.getByRole('button', { name: 'Registrar saída' }).click()

  await expect(page.getByText('Todos os pontos do roteiro foram concluídos.')).toBeVisible()
})

// C2 · Regra que barra erro — roteiro precisa de partida + uma parada (RF04 / RN06)
//   Dado que existe um motorista cadastrado
//   Quando tento gerar um roteiro com apenas 1 endereço
//   Então vejo o aviso "Informe pelo menos dois pontos (partida + uma parada)."
//          e nenhum roteiro é criado para o motorista
test('recusa gerar um roteiro com um único ponto', async ({ page }) => {
  const motorista = nomeUnico('Motorista')
  await entrarComoAdmin(page)
  await cadastrarMotorista(page, motorista)

  const roteiros = page.getByRole('tabpanel', { name: 'Roteiros (RF04)' })
  await page.getByRole('tab', { name: 'Roteiros (RF04)' }).click()
  await escolher(page, 'Motorista responsável', motorista)
  await roteiros.getByLabel('Endereços avulsos').fill('Rua Sozinha, 1')
  await roteiros.getByRole('button', { name: 'Gerar roteiro' }).click()

  await expect(page.getByRole('alert')).toHaveText('Informe pelo menos dois pontos (partida + uma parada).')
  await expect(page.getByText(/Roteiro criado/)).toHaveCount(0)

  await irPara(page, 'Registro de Ponto')
  await escolher(page, 'Motorista', motorista)
  await expect(page.getByText('Nenhum roteiro atribuído para este motorista nesta data.')).toBeVisible()
})
