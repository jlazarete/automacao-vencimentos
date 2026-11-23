# Política de Segurança

Este projeto trata dados pessoais (LGPD). Por isso, a regra principal vale para qualquer pessoa que contribua ou relate problemas:

> [!WARNING]
> Nunca publique planilhas, logs, prints de e-mail ou credenciais reais em issues, pull requests ou comentários. Use somente dados fictícios.

## Como relatar uma vulnerabilidade

Não abra uma issue pública. Use o relato privado do GitHub: aba **Security** do repositório, botão **Report a vulnerability**.

Inclua, sempre com dados fictícios: o que você encontrou, como reproduzir e qual o impacto percebido.

## Versões com suporte

Apenas a branch `main` recebe correções de segurança.

## O que o projeto já faz

- Segredos ficam em variáveis de ambiente e GitHub Secrets, nunca no código.
- Planilha lida em memória; nenhum arquivo com dados pessoais é gravado em disco.
- Logs e histórico de envios não guardam nome, e-mail ou telefone de clientes.
- Base de compliance anonimizada por padrão: coluna desconhecida é removida.
- Conexão SMTP com validação de certificado; HTML do e-mail com escape de todo dado da planilha.
- Testes automatizados de privacidade e segurança, análise estática (Bandit) e auditoria de dependências no CI.
