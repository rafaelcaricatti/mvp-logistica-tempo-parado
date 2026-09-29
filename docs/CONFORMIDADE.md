# Verificação de conformidade com a Especificação de Requisitos

Confronto item a item entre a *Especificação de Requisitos — MVP Sistema de
Monitoramento de Tempo Parado em Roteiros* e o que foi implementado.

Legenda: ✅ atendido · ⚠️ atendido com ressalva · ➖ fora do escopo (corretamente não implementado)

---

## 2. Objetivo do MVP

| Objetivo | Situação | Onde |
|---|---|---|
| Identificar quanto tempo o profissional fica parado em cada ponto | ✅ | `services/calculo.py`, `POST /roteiros/{id}/pontos/{ordem}/chegada` e `/saida` |
| Registrar e persistir pontos, roteiros e tempos | ✅ | Cloud Firestore (`repositories.py`, `core/firebase.py`) |
| Painel com gráficos por dia, mês e período | ✅ | `GET /dashboard`, tela *Dashboard* |
| Calcular indicadores de custo (custo/km, km/litro) | ✅ | `calculo.calcular_custo`, `GET /parametros` |

---

## 3. Escopo

### 3.1 Dentro do escopo

| Item | Situação | Onde |
|---|---|---|
| Cadastro de motoristas/motoboys | ✅ | `/motoristas` |
| Cadastro de gerentes/coordenadores | ✅ | `/gerentes` |
| Cadastro de pontos | ✅ | `/pontos` |
| Cadastro de roteiros | ✅ | `/roteiros` |
| Coleta (endereço, data/hora de chegada e saída) | ✅ | `/roteiros/{id}/pontos/{ordem}/chegada` e `/saida` |
| Tempo parado por ponto e total do roteiro | ✅ | `calculo.tempo_parado_da_parada`, `calculo.tempo_total_parado` |
| Histórico por período, com endereços | ✅ | `GET /historico` |
| Dashboard por dia, mês e período | ✅ | `GET /dashboard?agrupamento=dia\|mes\|periodo` |
| Parametrização de custos e jornada | ✅ | `GET/PUT /parametros` |

### 3.2 Fora do escopo — confirmado que **não** foi implementado

| Item | Situação |
|---|---|
| Roteirização automática / otimização de rotas | ➖ a ordem dos pontos é definida por quem monta o roteiro |
| Integração com folha de pagamento ou ERP | ➖ |
| Telemetria embarcada / rastreamento em tempo real | ➖ os horários são marcados manualmente |
| Aplicativo nativo em loja | ➖ é uma aplicação web |

---

## 4. Regras de negócio

| ID | Regra | Situação | Implementação | Teste |
|---|---|---|---|---|
| RN01 | Ponto de partida não conta tempo parado | ✅ | `calculo.tempo_parado_da_parada` devolve `0.0` para `ordem == 1` | `test_rn01_ponto_de_partida_nao_conta_tempo` |
| RN02 | Tempo parado = saída − chegada | ✅ | mesma função; saída anterior à chegada é recusada com HTTP 422 | `test_rn02_tempo_parado_e_saida_menos_chegada`, `test_saida_antes_da_chegada_e_recusada` |
| RN03 | Total = soma dos pontos, exceto a partida | ✅ | `calculo.tempo_total_parado` | `test_rn03_total_soma_tudo_menos_a_partida` (15+10+50 = 75 min, roteiro A da seção 5) |
| RN04 | Jornada padrão de 8 h como base percentual | ✅ | `calculo.percentual_jornada`; parâmetro `jornada_horas` = 8.0 | `test_rn04_percentual_da_jornada_de_8_horas` (75/480 = 15,62 %) |
| RN05 | Um roteiro = um motorista + uma data | ✅ | campos `motorista_id` e `data` no documento do roteiro | `test_rn05_roteiro_tem_um_motorista_e_uma_data` |
| RN06 | Pontos em ordem sequencial 1, 2, 3… | ✅ | `roteiros._resolver_paradas` numera automaticamente; a coleta exige a ordem (HTTP 409 se pular) | `test_rn06_pontos_em_ordem_sequencial`, `test_ordem_sequencial_e_exigida_na_coleta` |
| RN07 | Custo a partir de combustível, km/l e distância | ✅ | `calculo.calcular_custo` | `test_rn07_e_rf11_custo_do_trajeto` |

---

## 5. Exemplo de roteiro (seção 5)

Os roteiros **A**, **B** e **C** da especificação são criados pela carga de
demonstração (`backend/app/services/seed.py`), com os tempos exatos do
documento:

| Roteiro | Tempos por ponto (min) | Total |
|---|---|---|
| A | partida, 15, 10, 50 | 75 |
| B | partida, 10, 5, 26 | 41 |
| C | partida, 5, 10, 30 | 45 |

Os tempos **não são gravados direto**: a carga registra chegada e saída, e o
valor sai do cálculo — do mesmo jeito que acontece no uso real.

---

## 6. Requisitos funcionais

| ID | Requisito | Prioridade | Situação | Endpoint / tela | Teste |
|---|---|---|---|---|---|
| RF01 | Cadastrar motorista (nome, telefone, documento, veículo) | Alta | ✅ | `/motoristas` · *Cadastros → Motoristas* | `test_rf01_cadastro_de_motorista` |
| RF02 | Cadastrar gerente (nome, telefone, e-mail) | Alta | ✅ | `/gerentes` · *Cadastros → Gerentes* | `test_rf02_cadastro_de_gerente` |
| RF03 | Cadastrar pontos com endereço e coordenadas | Alta | ✅ | `/pontos` · *Cadastros → Pontos* (com mapa) | `test_rf03_cadastro_de_ponto_com_coordenadas` |
| RF04 | Montar roteiro diário (pontos em ordem, motorista, data) | Alta | ✅ | `POST /roteiros` · *Cadastros → Roteiros* | `test_rf04_monta_roteiro_a_partir_de_pontos_cadastrados` |
| RF05 | Registrar chegada e saída em cada ponto | Alta | ✅ | `/roteiros/{id}/pontos/{ordem}/chegada` e `/saida` · *Registro de Ponto* | `test_rf05_registro_de_chegada_e_saida` |
| RF06 | Calcular tempo parado por ponto e total | Alta | ✅ | recalculado e gravado a cada marcação | `test_rf06_calculo_automatico` |
| RF07 | Histórico de pontos e tempos por período, com endereços | Alta | ✅ | `GET /historico` · *Histórico* | `test_rf07_historico_traz_endereco_e_horarios` |
| RF08 | Dashboard com gráficos por dia, mês e período | Alta | ✅ | `GET /dashboard` · *Dashboard* | `test_rf08_dashboard_nos_tres_recortes` |
| RF09 | Parametrizar custos (combustível, km/l, custo por km) | Média | ✅ | `PUT /parametros` · *Configurações* | `test_rf09_rf10_parametros_alteraveis_sem_mexer_no_codigo` |
| RF10 | Parametrizar regras de cálculo e jornada (8 h/dia) | Média | ✅ | `jornada_horas`, `contar_ponto_partida`, `tolerancia_minutos`, `arredondamento_minutos` | `test_rf10_arredondamento_configuravel` |
| RF11 | Calcular custo estimado do roteiro | Média | ✅ | `custo_detalhado` em todo roteiro | `test_rn07_e_rf11_custo_do_trajeto` |
| RF12 | Exportar relatórios do período consultado | Baixa | ✅ | `/relatorios/historico.csv` e `/relatorios/completo` · botão em *Histórico* | `test_rf12_exportacao_csv_e_relatorio` |

### Detalhe do RF10

A especificação pede "parametrizar **regras de cálculo** do tempo parado". Além
da jornada, ficaram configuráveis pela tela, sem tocar em código:

- **Contar o ponto de partida** — desligado por padrão (RN01), mas pode ser ligado
- **Tolerância por parada** — paradas abaixo de N minutos são desprezadas
- **Arredondamento** — granularidade do tempo (1 min, 5 min, 15 min…)

---

## 7. Requisitos não funcionais

| ID | Requisito | Situação | Como foi atendido |
|---|---|---|---|
| RNF01 | Persistência em banco, com histórico completo | ✅ | Cloud Firestore via `firebase-admin`; nada fica só em memória. Verificado reiniciando a API e reconsultando os dados |
| RNF02 | Interface web responsiva (desktop e celular) | ⚠️ | Streamlit com layout em colunas, que empilham em tela estreita — funciona no navegador do celular. Não foi feito teste em dispositivo físico nem ajuste fino de CSS |
| RNF03 | Dashboard abaixo de 3 s para consultas de 12 meses | ✅ | Consulta filtrada por faixa de data no Firestore + agregação em memória. Toda resposta traz o cabeçalho `X-Tempo-Resposta-ms`. Teste com 60 roteiros e 12 meses respondeu em milissegundos |
| RNF04 | Controle de acesso por perfil | ✅ | Três perfis (`motorista`, `gerente`, `administrador`), token assinado, dependências `requer_perfil`. O motorista só enxerga e marca os próprios roteiros |
| RNF05 | Auditoria das alterações em pontos e horários | ✅ | Coleção `auditoria` grava usuário, ação, entidade, valor anterior e valor novo em cada marcação e alteração. Consultável em `GET /auditoria` e na tela *Administração* |
| RNF06 | Aderência à LGPD | ⚠️ | Senhas em PBKDF2-HMAC-SHA256 com salt, nunca devolvidas pela API; coleta mínima de dados pessoais; acesso direto ao Firestore bloqueado por `firestore.rules`; credenciais fora do Git; rotas `DELETE` atendem ao direito de eliminação; auditoria de quem acessou o quê. **Não** foram implementados fluxos formais de consentimento, política de privacidade nem anonimização automática após prazo de retenção |

---

## 8. Modelo de dados

| Entidade da especificação | Coleção no Firestore | Atributos |
|---|---|---|
| **Ponto** | `pontos` (cadastro) + array `pontos` dentro de `roteiros` (parada) | `id`, `endereco`, `latitude`, `longitude`, `chegada`, `saida`, `tempo_parado_min`, `ordem` — ✅ todos |
| **Roteiro** | `roteiros` | `id`, `data`, `motorista_id`, lista ordenada de pontos, `distancia_total_km`, `tempo_total_parado_min`, `custo_estimado` — ✅ todos |
| **Motorista / Motoboy** | `motoristas` | `id`, `nome`, `telefone`, `documento`, `veiculo`, `rendimento_km_l` — ✅ todos |
| **Gerente / Coord. / Dono** | `gerentes` | `id`, `nome`, `telefone`, `email`, `equipe` — ✅ todos |
| **Parâmetro** | `parametros` (documento único `global`) | `valor_combustivel`, `rendimento_km_l_padrao`, `custo_por_km`, `jornada_horas`, regras de cálculo — ✅ todos |

Coleções adicionais, exigidas pelos requisitos não funcionais:
`usuarios` (RNF04) e `auditoria` (RNF05).

**Decisão de modelagem:** as paradas ficam como array ordenado dentro do
documento do roteiro, em vez de subcoleção. A especificação descreve o roteiro
como tendo uma "lista ordenada de pontos", o roteiro é sempre lido inteiro, e
assim cada marcação de horário é uma escrita atômica em um documento só.

---

## 9. Entregáveis

| Entregável | Situação | Observação |
|---|---|---|
| Dashboard com gráficos por dia, mês e período | ✅ | tela *Dashboard* |
| Histórico de pontos e tempos por período, com endereços | ✅ | tela *Histórico*, com exportação |
| Módulo de coleta dos pontos do roteiro | ✅ | tela *Registro de Ponto* |
| Entrada de pedidos e identificação dos endereços para o roteiro | ⚠️ | Ver ressalva abaixo |
| Parâmetros de custo | ✅ | tela *Configurações* |
| Parâmetros de cálculo do tempo parado, com 8 h/dia | ✅ | tela *Configurações* |
| Camada de persistência (pontos, roteiros, motoristas, gerentes) | ✅ | Firestore |
| Documento de especificação (1ª parte) | ➖ | É o entregável da 1ª parte, já feito — o PDF na raiz. O complemento em `docs/modelo-conceitual.md` traz o modelo de classes e os casos de uso do que foi construído |
| Pontos extras: nome do produto e campanha | ⚠️ | O nome **ParouAí** foi adotado no sistema. A campanha de divulgação é material de marketing e não foi produzida |

### Ressalva sobre "entrada de pedidos"

A seção 9 cita *"módulo de coleta de dados dos pontos do roteiro (entrada de
pedidos) e identificação dos endereços dos pedidos para o roteiro"*. Uma
entidade **Pedido** não aparece em nenhum outro lugar do documento: não está no
modelo de dados (seção 8), não tem requisito funcional (seção 6) nem regra de
negócio (seção 4).

A leitura adotada foi a de que "pedido" é o destino de entrega, e o que o
sistema precisa dele é o endereço. Assim, a entrada de pedidos acontece em dois
lugares:

- **Cadastros → Pontos**: endereço + coordenadas dos destinos recorrentes (RF03)
- **Cadastros → Roteiros**: seleção dos pontos na ordem do trajeto, mais um
  campo de endereços avulsos, um por linha, para pedidos que não têm cadastro

Se a intenção for uma entidade `Pedido` completa (número, cliente, janela de
entrega, status), isso é um acréscimo ao escopo dos RFs e pode ser feito sem
quebrar o que existe — a `ParadaCreate` já aceita um identificador externo.

---

## 10. Critérios de aceitação

| Critério | Situação | Evidência |
|---|---|---|
| O sistema não computa tempo parado no ponto de partida | ✅ | `test_rn01_ponto_de_partida_nao_conta_tempo`; a tela marca o ponto 1 como "não conta" |
| O dashboard apresenta os três recortes: dia, mês e período | ✅ | `test_rf08_dashboard_nos_tres_recortes`; seletor *Recorte de visualização* |
| Todo tempo parado exibido está vinculado a um endereço e a uma data/hora registrados | ✅ | `test_rf07_historico_traz_endereco_e_horarios`; o CSV traz endereço, chegada e saída em cada linha |
| Os parâmetros de custo e de jornada podem ser alterados sem alteração de código | ✅ | `test_rf09_rf10_parametros_alteraveis_sem_mexer_no_codigo`; os parâmetros vivem no Firestore e são editados em *Configurações* |

---

## Como esta verificação foi feita

1. **Testes automatizados** — `pytest -q` roda 31 testes que exercitam a API de
   ponta a ponta e a interface. Cada regra e requisito acima aponta o teste
   correspondente.
2. **Execução contra o Firestore de verdade** — a aplicação foi rodada contra o
   emulador oficial do Firestore (mesmo SDK e mesmo protocolo do Firebase em
   nuvem), com carga de 40 roteiros: consultas compostas, filtros por faixa de
   data e ordenação funcionaram, e os dados continuaram lá depois de reiniciar
   a API (RNF01).
3. **Navegação pela interface** — as seis telas foram abertas nos perfis de
   administrador e de motorista, conferindo gráficos, indicadores, tabelas e as
   restrições de acesso.

### Resumo

- **7 de 7** regras de negócio: atendidas
- **12 de 12** requisitos funcionais: atendidos
- **6 de 6** requisitos não funcionais: 4 atendidos, 2 com ressalva (RNF02 e RNF06)
- **4 de 4** critérios de aceitação: atendidos
- **Entregáveis:** todos os de software entregues; ressalvas em "entrada de
  pedidos" e na campanha de divulgação (material de marketing)
