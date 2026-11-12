// Teste de aceitação do ParouAí — cenário 3 (regra de estado).
// RF05 / RNF: as marcações de chegada e saída ficam gravadas no servidor, não na
// tela. Recarregar a página derruba a sessão do navegador (o Streamlit esquece
// tudo e pede login de novo), mas o andamento do roteiro tem de continuar lá.
const { test, expect } = require('@playwright/test')
const { nomeUnico, entrarComoAdmin, irPara, cadastrarMotorista, escolher, montarRoteiro } = require('./ajuda')

// C3 · Regra de estado — o andamento do roteiro sobrevive a recarregar a página
//   Dado que um motorista tem um roteiro de 3 pontos, já saiu do ponto 1 e
//        registrou a chegada no ponto 2
//   Quando recarrego a página e entro de novo no sistema
//   Então o roteiro continua no ponto 2, com a chegada já registrada: aparece
//        "Registrar saída" e não aparece mais "Registrar chegada"
test('o andamento do roteiro continua igual depois de recarregar a página', async ({ page }) => {
  const motorista = nomeUnico('Motorista')
  await entrarComoAdmin(page)
  await cadastrarMotorista(page, motorista)
  await montarRoteiro(page, motorista, ['Rua A, 1', 'Rua B, 2', 'Rua C, 3'])

  await irPara(page, 'Registro de Ponto')
  await escolher(page, 'Motorista', motorista)
  await expect(page.getByRole('heading', { name: /Ponto 1: Rua A, 1/ })).toBeVisible()
  await page.getByRole('button', { name: 'Registrar chegada' }).click()
  await page.getByRole('button', { name: 'Registrar saída' }).click()
  await expect(page.getByRole('heading', { name: /Ponto 2: Rua B, 2/ })).toBeVisible()
  await page.getByRole('button', { name: 'Registrar chegada' }).click()
  await expect(page.getByRole('button', { name: 'Registrar saída' })).toBeVisible()

  // Recarregar zera a sessão do navegador: a prova é que o login volta a aparecer.
  await page.reload()
  await expect(page.getByRole('button', { name: 'Entrar' })).toBeVisible()

  await entrarComoAdmin(page)
  await irPara(page, 'Registro de Ponto')
  await escolher(page, 'Motorista', motorista)

  await expect(page.getByRole('heading', { name: /Ponto 2: Rua B, 2/ })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Registrar saída' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Registrar chegada' })).toHaveCount(0)
})
