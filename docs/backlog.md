# Quadro Kanban de Tarefas e Backlog

---
<p align="center">
  <a href="../README.md">Início</a> •
  <a href="README.md">Índice Geral</a> •
  <strong>Backlog/Kanban</strong> •
  <a href="execucao-local.md">Execução Local</a> •
  <a href="gerar-senha-app-google.md">Senha App Google</a> •
  <a href="configuracao-github-actions.md">GitHub Secrets</a> •
  <a href="token-dropbox.md">API Dropbox</a> •
  <a href="PLANO_RESILIENCIA.md">Resiliência & Logs</a> •
  <a href="sincronizacao-notebooklm.md">NotebookLM</a>
</p>
---

Este quadro gerencia as tarefas pendentes, em andamento e concluídas do projeto de automação.

---

## Quadro Kanban

| A Fazer (To Do) | Em Progresso (In Progress) | Concluído (Done) |
| :--- | :--- | :--- |
| *(nenhum item)* | *(nenhum item)* | - [x] Validar migração de diretórios <br> - [x] Validar disparo real de e-mail do robô com planilha fictícia (20 dias de antecedência) <br> - [x] Concluir a janela de teste com planilha fictícia <br> - [x] Correções de segurança: TLS verificado, escape de HTML e URL, logs sem dados pessoais, histórico de envios com hash <br> - [x] Motor LGPD com falha fechada (coluna desconhecida é removida) <br> - [x] Testes automatizados de privacidade e segurança no CI <br> - [x] Revisão final de segurança e publicação do repositório como case (licença MIT, histórico anonimizado, proteções do GitHub) <br> - [x] Gerador de planilha fictícia para demonstração <br> - [x] [Automação da Sincronização do NotebookLM](#automação-da-sincronização-do-notebooklm) <br> - [x] Manual para configurar múltiplos remotos Git ([implantação no cliente](implantacao-cliente.md)) <br> - [x] Implantação no repositório do cliente (considerada concluída pelo autor em 23/11/2026) |

> [!NOTE]
> Não há itens em aberto. O passo a passo da implantação continua disponível em [implantacao-cliente.md](implantacao-cliente.md). O teste de ponta a ponta com o Gmail e o Dropbox reais foi dado como feito e aprovado pelo autor em 23/11/2026. Antes de operar em produção, remova do Dropbox qualquer planilha de teste (veja [Planilha Fictícia](sincronizacao-notebooklm.md)).

---

## Validação com Planilha Fictícia

O disparo de alerta do `main.py` foi validado de ponta a ponta com uma planilha de teste
(`clientes_teste.xlsx`, somente dados fictícios) como a planilha `.xlsx` mais recente da raiz do Dropbox.

- O script `scripts/gerar_planilha_ficticia.py` cria essa planilha com dados claramente fictícios
  (veja [Sincronização do NotebookLM e Planilha Fictícia](sincronizacao-notebooklm.md)).
- O script `atualizar_datas_dropbox.py` baixa a planilha de teste, reescreve uma linha por dia
  com vencimento em `hoje + 20 + i` dias e sobe o arquivo de volta. Assim, cada dia da janela
  de teste aciona o gatilho de 20 dias de antecedência.
- O script só altera arquivos cujo nome contenha `teste` e exige o argumento `--confirmar`.
  Uma planilha de produção nunca é tocada.
- Ao rodar `main.py`, o gatilho dispara, o e-mail de alerta chega ao Gestor, e a chave do envio
  é gravada em `enviados.json` (somente um hash, sem nome de cliente) para não duplicar o alerta.
- A pasta local `dados_teste/` (origem da planilha fictícia) está no `.gitignore` e não deve ser versionada.

> [!NOTE]
> Enquanto uma planilha de teste for o `.xlsx` mais recente da pasta monitorada, a planilha
> real fica fora do processamento do robô. Remova o arquivo de teste do Dropbox antes de operar em produção.

---

## Automação da Sincronização do NotebookLM

> [!TIP]
> **Concluída.** O script `scripts/sync_notebooklm.py` gera um arquivo consolidado (`notebooklm_context.md`) com o código e a documentação versionados, copia para o Google Drive e avisa por e-mail. Detalhes e comandos em [sincronizacao-notebooklm.md](sincronizacao-notebooklm.md).

### Escopo e Tarefas:
- [x] **Configuração do Ambiente:**
  - Variável `GOOGLE_DRIVE_PATH` no `.env` indica a pasta do Google Drive local (modelo em `.env.example`).
- [x] **Desenvolvimento do Script de Consolidação:**
  - `scripts/sync_notebooklm.py` reúne os arquivos de texto versionados e os últimos commits em um único Markdown. Aborta se achar um segredo.
- [x] **Integração e Cópia:**
  - A opção `--copiar` copia o arquivo para a pasta configurada do Google Drive.
- [x] **Sistema de Notificação:**
  - A opção `--notificar` envia e-mail via SMTP (`EMAIL_USER` e `EMAIL_PASS`, com certificado validado) avisando que o contexto foi atualizado. O e-mail não leva conteúdo do projeto.
- [x] **Gatilho de Automação:**
  - Hook de Git pronto em `scripts/hooks/post-commit`, de instalação opcional (comando no manual).

---

## Atalhos de Referência
* **Manual de Implantação:** [Como Criar o Repositório no GitHub do Cliente](implantacao-cliente.md)
* **Central de Documentação:** [docs/README.md](README.md)
