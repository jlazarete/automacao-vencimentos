# Como Gerar a Senha de App do Google (Gmail)

---
<p align="center">
  <a href="../README.md">Início</a> •
  <a href="README.md">Índice Geral</a> •
  <a href="backlog.md">Backlog/Kanban</a> •
  <a href="execucao-local.md">Execução Local</a> •
  <strong>Senha App Google</strong> •
  <a href="configuracao-github-actions.md">GitHub Secrets</a> •
  <a href="token-dropbox.md">API Dropbox</a> •
  <a href="PLANO_RESILIENCIA.md">Resiliência & Logs</a>
</p>
---

Este guia orienta o passo a passo de como gerar uma senha de aplicativo segura para permitir que o robô envie os e-mails de alerta utilizando o protocolo seguro da sua conta Google corporativa ou pessoal.

---

## Pré-requisito Obrigatório

> [!IMPORTANT]
> A conta de e-mail remetente precisa estar com a **Verificação em Duas Etapas** ativada nas configurações de segurança do Google. Caso contrário, a opção "Senhas de app" estará oculta pelo sistema.

---

## Passo a Passo Atualizado

1. **Acesse a sua Conta Google:**
   - Entre na área principal [Gerenciar sua Conta do Google](https://myaccount.google.com).
2. **Navegue até o menu de Segurança:**
   - No menu lateral esquerdo (ou superior, se estiver em dispositivos móveis), clique em **Segurança**.
3. **Localize a busca direta:**
   - Vá até a barra de pesquisa localizada no topo da página de segurança (ícone de lupa).
4. **Pesquise pelo termo correto:**
   - Digite exatamente **"Senhas de app"** (ou *App passwords* se a sua conta estiver configurada em inglês) e clique no atalho sugerido pelo sistema.
5. **Crie a Credencial do Robô:**
   - No campo **Nome do app**, digite algo fácil de identificar, como: `Script Alerta Renovacao Dropbox`.
   - Clique no botão **Criar**.
6. **Copie o código gerado:**
   - Uma janela pop-up será exibida contendo uma senha de **16 caracteres** dentro de um bloco destacado.
   - **Copie essa senha imediatamente** e salve-a temporariamente (ela não será exibida novamente).

> [!TIP]
> Não é necessário copiar os espaços intermediários que aparecem na tela; o script utiliza a sequência corrida de 16 letras direto.

---

## Nota para Contas Google Workspace (E-mail Corporativo)

> [!WARNING]
> Se o e-mail do cliente for sob um domínio próprio (ex: `nome@empresa.com`), o **Administrador de TI da empresa** precisará liberar previamente a permissão para "Senhas de app" no painel central do Google Workspace Console. Se estiver desativado pela governança interna, a opção não aparecerá na busca do usuário.
