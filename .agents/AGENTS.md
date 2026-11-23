# Diretrizes de Comportamento do Agente (Workspace Rules)

Este arquivo define regras de comportamento persistentes que devem ser seguidas pelo agente de IA sempre que interagir neste repositório.

## Regras de Execução (Linux, bash)
- O ambiente de referência é Linux (Ubuntu/Debian) com bash, o mesmo do GitHub Actions. Escreva comandos, exemplos e documentação primeiro para Linux.
- Use `python3`. O comando `python` só existe dentro do `.venv` ativado (`source .venv/bin/activate`). Se faltar o módulo `venv`: `sudo apt install python3-venv`.
- Não crie scripts `.ps1`, `.bat` nem comandos específicos de Windows. Se for inevitável citar Windows, deixe como nota secundária (veja o apêndice de `docs/execucao-local.md`).
- Use caminhos com `/` e `pathlib`/`os.path.join`; finais de linha são LF (veja `.gitattributes`).

## 📦 Versionamento de Código (Git)
- Nunca commitar nem fazer push sem pedido explícito do José — trabalho pronto e não commitado é estado normal, ele revisa o diff antes de decidir. Ao terminar uma tarefa (melhoria de layout, correção de bug, desenvolvimento funcional), deixe as alterações no working tree e informe o que mudou.
- Quando ele pedir o commit, o fluxo é:
  1. `git add <arquivos>`
  2. `git commit -m "mensagem descritiva do commit"`
  3. `git push` (só se ele pedir explicitamente)
- Quando for solicitado consolidar ou mesclar a branch de desenvolvimento (`dev`) na branch principal (`main`), o fluxo a ser seguido pelo terminal é:
  1. `git checkout main`
  2. `git merge dev`
  3. `git push origin main`
  4. `git checkout dev` (para retornar à branch de trabalho)


## 📁 Governança de Diretório
- O diretório do projeto é a raiz deste repositório (`automacao-vencimentos/`). Quaisquer comandos do terminal devem ser executados a partir desta raiz.

## Privacidade e Segurança (regras para qualquer contribuição)
- Nunca escrever em código, documentação, commits, issues ou logs: nome, e-mail, telefone, CPF/CNPJ, apólice ou qualquer outro dado real de cliente. Exemplos e testes usam somente dados fictícios (domínio `exemplo.invalido`).
- Não registrar em log nomes de clientes, caminhos do Dropbox ou mensagens de exceção de bibliotecas. Use `mascarar_nome()` e `descrever_erro()` de `main.py`.
- Todo valor vindo da planilha e colocado em HTML passa por `escape()`; em URL, por `quote()`.
- Coluna nova na planilha sai removida da base anonimizada até ser classificada em `lgpd_engine.py`.
- Antes de qualquer commit: `python3 teste_lgpd.py`, `python3 teste_seguranca.py` e `python3 teste_scripts.py`.

## 📝 Padrão de Formatação de Documentação (Visual Padrão Limpo e Organizado)
- **Visual Limpo e Técnico:** Evite usar emoticons em cabeçalhos (títulos `#`, `##`, `###`). Mantenha os títulos puramente textuais e sóbrios.
- **Cabeçalho Centralizado:** O README principal de cada projeto deve iniciar com título `<h1 align="center">` e descrição `<p align="center">` centralizados, acompanhados de badges Shields.io estilizados para o projeto.
- **Barra de Navegação Minimalista:** Em subpastas de documentação (como `/docs`), utilize uma barra de links em texto simples centralizada (sem ícones e sem código HTML poluído). O manual ativo deve vir destacado em negrito (ex: `**Manual**`) e os demais com links markdown normais, separados por ` • `.
- **Sem Ícones Excessivos:** Use ícones e emoticons de maneira extremamente pontual e discreta, apenas onde agregarem real valor visual sem poluir a leitura.
