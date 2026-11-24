# Guia de Implantação no Cliente (Múltiplos Remotos Git)

---
<p align="center">
  <a href="../README.md">Início</a> •
  <a href="README.md">Índice Geral</a> •
  <a href="backlog.md">Backlog/Kanban</a> •
  <strong>Implantação</strong> •
  <a href="execucao-local.md">Execução Local</a> •
  <a href="gerar-senha-app-google.md">Senha App Google</a> •
  <a href="configuracao-github-actions.md">GitHub Secrets</a> •
  <a href="token-dropbox.md">API Dropbox</a> •
  <a href="PLANO_RESILIENCIA.md">Resiliência & Logs</a>
</p>
---

Este manual descreve a estratégia adotada para implantar o código das automações diretamente no GitHub do cliente, mantendo o histórico de desenvolvimento isolado no repositório pessoal.

> [!IMPORTANT]
> A implantação envia ao cliente o **histórico completo** do repositório de origem. Faça o envio a partir de um repositório com histórico limpo (sem e-mail pessoal, caminhos locais ou dados de outros clientes). No repositório público do case só existe a branch `main`, então o passo de `merge` da branch `dev` abaixo se aplica apenas ao repositório de desenvolvimento.

---

## Fluxo de Configuração

### Passo 1: Criar o repositório no GitHub do cliente
1. Crie a conta do seu cliente no GitHub (ou acesse a conta existente).
2. Crie um repositório novo e **vazio** para o projeto (ex: `automacao-vencimentos`).
3. **Não** inicialize com README, .gitignore ou licença. Deixe-o totalmente vazio.

### Passo 2: Configurar Permissão de Acesso
Para que você possa enviar código da sua máquina sem precisar trocar de conta no Git:
1. No repositório do cliente no site do GitHub, acesse **Settings** > **Collaborators** > **Add people**.
2. Digite o seu usuário do GitHub pessoal (ex: `jlazarete`) e envie o convite.
3. Acesse o seu próprio e-mail ou conta do GitHub e **aceite o convite**.

### Passo 3: Registrar o Repositório do Cliente localmente
No terminal do seu projeto local, adicione o novo repositório com o apelido de `cliente`:
```bash
git remote add cliente https://github.com/usuario-do-cliente/nome-do-repositorio.git
```
*Substitua a URL acima pela URL do repositório que foi criado no GitHub do cliente.*

Para verificar se foi cadastrado com sucesso:
```bash
git remote -v
```

---

## Fluxo de Trabalho e Atualizações (Dia a Dia)

Toda vez que finalizar um desenvolvimento e quiser implantar a versão estável no cliente:

1. Garanta que todas as alterações da branch `dev` foram testadas e mescladas na branch `main`:
   ```bash
   git checkout main
   git merge dev
   ```
2. Faça o envio da branch `main` diretamente para o repositório do cliente:
   ```bash
   git push cliente main
   ```
3. Volte para a branch `dev` para continuar os desenvolvimentos diários:
   ```bash
   git checkout dev
   ```
