# Estratégia de Evolução: Automação Inteligente (Python e n8n)

---
<p align="center">
  <a href="../README.md">Início</a> •
  <a href="README.md">Índice Geral</a> •
  <a href="backlog.md">Backlog/Kanban</a> •
  <a href="execucao-local.md">Execução Local</a> •
  <a href="gerar-senha-app-google.md">Senha App Google</a> •
  <a href="configuracao-github-actions.md">GitHub Secrets</a> •
  <a href="token-dropbox.md">API Dropbox</a> •
  <strong>Resiliência & Logs</strong> •
  <a href="sincronizacao-notebooklm.md">NotebookLM</a>
</p>
---

Este documento descreve a estratégia dividida em duas fases evolutivas para a automação de seguros, focando em resiliência (retry logic) e observabilidade (logs).

---

## Momento 1: Evolução da Automação Atual (100% Python)

No cenário atual, todo o processamento e acionamento estão centralizados no Python via GitHub Actions. O foco aqui é blindar o script contra instabilidades de rede e garantir a integridade dos logs.

### 1. Implementação de Retry Logic (Tenacity)
* **O Problema:** Conexões com Dropbox (API) e Gmail (SMTP) sofrem intermitências (micro-cortes). Um erro simples encerra todo o fluxo do robô imediatamente.
* **A Solução:** Adição da biblioteca `tenacity` para gerenciar retentativas inteligentes.
* **Implementação Técnica:** Uso do decorador `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))` sobre as funções críticas de `conectar_dropbox()`, `ler_excel_da_memoria()` e `enviar_email()`. O código passa a suportar até 3 falhas antes de realmente interromper o processo.

### 2. Geração Profissional de Logs (Módulo Logging)
* **O Problema:** Os logs ficavam armazenados na memória RAM (lista `novos_logs`). Se o container morresse (por OOM - Out of Memory ou Timeout no GitHub Actions), todos os logs daquela sessão eram perdidos para sempre, dificultando o *troubleshooting*.
* **A Solução:** Utilizar o módulo nativo `logging` do Python configurado com *handlers* duplos (Console e Arquivo).
* **Implementação Técnica:**
  - O log é escrito em tempo real em um arquivo local temporário (ex: `execucao.log`).
  - O fluxo principal roda dentro de um bloco de tratamento `try / finally`.
  - O bloco `finally` garante a tentativa de upload do arquivo `execucao.log` para o Dropbox, independentemente de o script ter rodado com sucesso ou falhado com exceções não mapeadas.

---

## Momento 2: Migração e Integração com n8n

No futuro, para escalar a visualização, criar painéis ou conectar mais ferramentas corporativas, parte da responsabilidade do GitHub Actions será migrada para o n8n. O Python será mantido apenas como o motor de regras complexas (manipulação do DataFrame).

### 1. Orquestração e Retry no n8n
* **Nova Dinâmica:** O n8n passa a ser o orquestrador (gatilho diário). Ele aciona o script Python (via nó *Execute Command* se estiver na mesma máquina ou *HTTP Request* para uma função Serverless) e espera a resposta.
* **Retry Logic:** O n8n fará as retentativas das chamadas de API utilizando a configuração nativa do nó (aba *Settings* -> *Retry On Fail* -> Max Tries: 3).

### 2. Tratamento de Erro Global (Error Trigger)
* **Arquitetura Resiliente:** Será criado um Workflow dedicado apenas para tratar erros, chamado "Global Error Handler".
* **Fluxo Principal:** O workflow principal será configurado para direcionar qualquer erro não recuperável para esse "Error Handler".
* **Notificação:** O "Error Handler" recebe o payload da falha, formata uma mensagem clara (identificando qual nó quebrou) e dispara um alerta para o celular do gestor de infraestrutura via webhook (Telegram/Slack).

### 3. Logs de Auditoria (Bancos de Dados)
* **Centralização de Dados:** O arquivo `.json` no Dropbox será substituído ou complementado por inserções em um banco de dados leve (PostgreSQL via Supabase ou Notion). Cada execução no n8n atualizará um painel de métricas.
