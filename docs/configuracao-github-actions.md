# Configuração das Credenciais no GitHub Secrets

---
<p align="center">
  <a href="../README.md">Início</a> •
  <a href="README.md">Índice Geral</a> •
  <a href="backlog.md">Backlog/Kanban</a> •
  <a href="execucao-local.md">Execução Local</a> •
  <a href="gerar-senha-app-google.md">Senha App Google</a> •
  <strong>GitHub Secrets</strong> •
  <a href="token-dropbox.md">API Dropbox</a> •
  <a href="PLANO_RESILIENCIA.md">Resiliência & Logs</a>
</p>
---

Para que o robô de automação execute diariamente na nuvem de forma segura e autônoma, as credenciais e tokens nunca devem ficar expostos no código do arquivo `main.py`. Eles são armazenados de forma criptografada nos Secrets do repositório.

---

## Como Cadastrar as Variáveis de Ambiente

1. **Acesse o repositório:**
   - Abra a página do projeto no **GitHub**.
2. **Navegue até as configurações:**
   - No menu superior de abas, clique na opção **Settings** (Configurações).
3. **Abra a seção de Secrets:**
   - No menu lateral esquerdo, role até a seção **Security** e clique na opção **Secrets and variables** -> **Actions**.
4. **Crie as variáveis:**
   - Para cada variável descrita abaixo, clique no botão verde **New repository secret**.

---

## Lista de Secrets Obrigatórios

Cadastre exatamente as seguintes chaves (respeitando letras maiúsculas e caracteres de sublinhado):

| Nome do Secret (Name) | Descrição do Conteúdo (Value) |
| :--- | :--- |
| `EMAIL_USER` | O endereço de e-mail completo do Gmail que disparará os alertas (ex: `seu-email@gmail.com`). |
| `EMAIL_PASS` | A senha de aplicativo de 16 dígitos gerada nas configurações do Google (sem espaços). |
| `DROPBOX_APP_KEY` | A Chave de Aplicativo (App Key) gerada no painel do Dropbox Developer. |
| `DROPBOX_APP_SECRET` | A Chave Secreta do Aplicativo (App Secret) gerada no painel do Dropbox Developer. |
| `DROPBOX_REFRESH_TOKEN` | O token de atualização de longa duração gerado para permitir o consumo constante da API do Dropbox. |

> [!TIP]
> Após preencher os campos `Name` e `Secret`, clique sempre no botão **Add secret** para salvar a credencial com segurança.

---

## Variáveis Opcionais (Repository Variables)

Além dos Secrets confidenciais, você pode configurar variáveis de texto visíveis em **Settings → Secrets and variables → Actions → Variables**:

| Nome da Variável | Padrão | Descrição |
| :--- | :--- | :--- |
| `DIAS_ANTECEDENCIA` | `20` | Janela de antecedência: alerta quando faltam esse número de dias ou menos (sem repetir). |
| `DROPBOX_PASTA` | *(raiz)* | Pasta no Dropbox onde o robô busca a planilha `.xlsx` mais recente. |

> [!NOTE]
> Se estas variáveis não forem configuradas manualmente, o robô utilizará os valores padrão pré-definidos no código automaticamente.

---

## Interruptor da Automação

O workflow diário só executa o robô quando a variável de repositório abaixo estiver definida. Sem ela (o caso de qualquer fork ou cópia do repositório), o job é pulado e nenhum e-mail é enviado.

| Nome da Variável | Valor | Efeito |
| :--- | :--- | :--- |
| `AUTOMACAO_ATIVA` | `true` | Liga o robô (cron diário e execução manual). Qualquer outro valor, ou a ausência da variável, mantém o robô desligado. |

> [!IMPORTANT]
> Para pausar a automação sem editar código, apague a variável `AUTOMACAO_ATIVA` ou troque o valor para `false`. Configure-a somente no repositório que roda em produção, nunca em cópias de demonstração.

> [!CAUTION]
> Rode a operação real **somente em repositório privado**. Em repositório público, o log do GitHub Actions é aberto a qualquer pessoa e, mesmo com nomes mascarados, mostra a quantidade de linhas e de alertas de cada execução, o que revela o tamanho da carteira do cliente.
