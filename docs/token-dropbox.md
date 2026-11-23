# Integração com a API do Dropbox e Refresh Token

---
<p align="center">
  <a href="../README.md">Início</a> •
  <a href="README.md">Índice Geral</a> •
  <a href="backlog.md">Backlog/Kanban</a> •
  <a href="execucao-local.md">Execução Local</a> •
  <a href="gerar-senha-app-google.md">Senha App Google</a> •
  <a href="configuracao-github-actions.md">GitHub Secrets</a> •
  <strong>API Dropbox</strong> •
  <a href="PLANO_RESILIENCIA.md">Resiliência & Logs</a> •
  <a href="sincronizacao-notebooklm.md">NotebookLM</a>
</p>
---

Este guia instrui como obter as credenciais de desenvolvedor do Dropbox necessárias para que o robô localize, leia e consuma dinamicamente as planilhas consolidadas diretamente da memória RAM.

---

## Passo 1: Criando o App no Dropbox Developer

1. **Acesse a área do desenvolvedor:**
   - Acesse o portal oficial [Dropbox Developers](https://www.dropbox.com/developers/apps).
2. **Login no Dropbox:**
   - Faça login com a conta onde a pasta e as planilhas de clientes estarão centralizadas.
3. **Criação do Aplicativo:**
   - Clique em **Create app** e selecione as seguintes configurações:
     - **Scoped access:** (Acesso baseado em escopos específicos).
     - **Full Dropbox** ou **App Folder** (dependendo de como deseja isolar o acesso aos arquivos).
     - Dê um nome único ao seu aplicativo (ex: `Robo-Alerta-Vencimentos`).
4. **Configuração de Escopos:**
   - Na aba **Permissions** do seu novo App, ative obrigatoriamente as seguintes permissões:
     - `files.metadata.read`
     - `files.content.read`
     - `files.content.write` (necessário para registrar o histórico de alertas enviados no arquivo `enviados.json`).
5. **Salvar alterações:**
   - Clique no botão **Submit** na parte inferior da página para aplicar os novos escopos de segurança.

---

## Passo 2: Copiando as Chaves Iniciais

Na aba principal **Settings** do seu aplicativo no Dropbox Developer, localize e copie as credenciais abaixo:
- **App key** (Chave pública de identificação do aplicativo).
- **App secret** (Chave privada/secreta usada para autenticação de requisições).

---

## Passo 3: Gerando o Refresh Token (Longa Duração)

> [!IMPORTANT]
> Como os tokens comuns do Dropbox expiram em apenas 4 horas por padrão de segurança da API, é obrigatório gerar um `Refresh Token` para garantir que o script funcione por tempo indeterminado de forma autônoma na nuvem.

1. **Obtenha o código de autorização inicial:**
   Substitua o termo `SUA_APP_KEY_AQUI` na URL abaixo com o valor copiado no Passo 2, cole no seu navegador e acesse:
   
   `https://www.dropbox.com/oauth2/authorize?client_id=SUA_APP_KEY_AQUI&token_access_type=offline&response_type=code`

2. **Autorize o acesso:**
   Clique em **Continuar** e aceite as permissões solicitadas na tela. O navegador exibirá um código temporário de autorização. Copie este código imediatamente.

3. **Gerar o token definitivo via terminal:**
   Abra o prompt de comando ou terminal da sua máquina e execute a requisição `curl` abaixo (substituindo as variáveis pelos seus dados reais):

   ```bash
   curl https://api.dropbox.com/oauth2/token \
     -d code=CODIGO_TEMPORARIO_GERADO_NO_PASSO_ANTERIOR \
     -d grant_type=authorization_code \
     -u SUA_APP_KEY:SEU_APP_SECRET
   ```

4. **Copiar o token retornado:**
   O terminal retornará uma resposta JSON contendo o campo `refresh_token`. Copie esse valor longo completo.

> [!TIP]
> Cadastre o `refresh_token` gerado nos Secrets do GitHub do projeto para que o GitHub Actions possa utilizá-lo diariamente.
