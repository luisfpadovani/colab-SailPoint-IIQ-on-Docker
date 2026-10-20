# Auditoria dos arquivos para publicação

Data: 20/10/2026. Branch preparada: `feature/security-review-source-only`.
Base inicial da consolidação: `origin/main` (`18e73b7`). Antes de preparar a PR, foi conferida e integrada a main oficial `upstream/main` (`eb80eb4`), que já contém o merge da V2 pela PR #3. A comparação de publicação usa essa base oficial atualizada.

## Escopo mantido no commit

- Dockerfiles, Compose, entrypoints e scripts de configuração criados/adaptados para o laboratório.
- Configurações específicas das integrações HR, JDBC e LDAP: aplicações, correlações, formulários, regras e tarefas.
- Scripts SQL próprios do appMock e healthcheck, sem scripts de schema/upgrade do produto.
- Fixtures sintéticas CSV/LDIF e schema dos atributos usados pelo exemplo.
- Testes, validadores, gerador Faker, automação de dependências e workflows de segurança.
- README, guia operacional, relatório consolidado dos dez pontos, esta auditoria, NOTICE e configuração de exclusões.

Os arquivos de governança já existentes na main foram preservados. O arquivo de imagem sem uso foi removido da árvore final. Os relatórios históricos locais de montagem e etapas intermediárias foram retirados do commit e preservados em `.secrets/reports-before-source-audit/`; a documentação publicada usa o relatório consolidado.

## Material que permanece somente local

- ZIP do IdentityIQ, JAR do patch, SSB ZIP e qualquer outro pacote/licenciado ou código compilado.
- Scripts SQL fornecidos pelo produto para criação/upgrade dos bancos IIQ.
- `.env`, valores codificados locais, chaves, certificados, logs e dependências temporárias.
- Export completo `UIConfig-Uiconfig.xml`, ausente da árvore final.

Os artefatos necessários ao build local não foram apagados. As exclusões do Git não alteram os mounts e secrets usados pelo Docker para construir a aplicação privada.

## Tratamento do histórico

A branch anterior `feature/security-review-hardening` não tinha binários na ponta, mas alcançava commits antigos com `sqljdbc4.jar`, o export UIConfig e credenciais de demonstração. Um push dessa branch transportaria esses objetos antigos, mesmo com os arquivos removidos no commit final.

Por isso, a branch de publicação foi criada diretamente da main e recebeu apenas a árvore final revisada em um novo commit. Não foi feito merge da branch antiga de hardening. A main oficial atualizada foi posteriormente integrada com preservação da árvore auditada; seus objetos históricos já publicados não são novos artefatos desta feature. A branch anterior continua disponível apenas como referência local; não deve ser publicada junto com a nova branch. Evitar publicação de todas as branches/tags por `--all` ou `--mirror`.

Esta consolidação não reescreve a main nem apaga conteúdo que já exista em repositórios remotos. A imagem histórica herdada da main não é um binário SailPoint e não é introduzida novamente pela feature; a árvore final não a contém.

## Controles de prevenção

- `.gitignore` ampliado para bloquear pacotes de qualquer versão, arquivos compilados, chaves/certificados e ambientes locais.
- `scripts/audit_sources.py` verifica os blobs reais do index e, com `--base`, todos os blobs novos do histórico. Rejeita extensões de pacote/binário, payload binário renomeado, chaves privadas, arquivos locais, scripts de produto conhecidos e o export UIConfig completo. O script não abre os artefatos locais ignorados nem imprime conteúdo dos blobs.
- Workflow de segurança verifica a árvore e o intervalo novo dos commits em PR/push, além do Gitleaks. `.gitignore` sozinho não impede `git add -f`; o auditor reprova esses arquivos mesmo quando forçados no index.
- Testes de regressão cobrem os bloqueios de caminhos/conteúdo e um pacote retirado da ponta mas ainda presente em um commit intermediário. O classificador é um controle técnico de artefatos; não determina a autoria de um texto por análise automática.

## Verificações de entrega

```bash
python3 scripts/audit_sources.py --base upstream/main
python3 scripts/validate.py
python3 -m unittest discover -s tests -p 'test_*.py'
git diff --cached --check
```

Os testes Python requerem `requirements-dev.txt`. Também foi executado Gitleaks sobre a árvore de fontes e sobre o histórico novo da branch consolidada. A auditoria verifica os arquivos staged e os objetos novos da branch, sem certificar todas as referências históricas locais.

A publicação deve selecionar explicitamente somente `feature/security-review-source-only`. O remote `origin` permanece no fork pessoal; `upstream` aponta para o projeto oficial. O intervalo da auditoria deve usar a main oficial atualizada. A PR remove os artefatos legados da árvore, sem reescrever o histórico da main.
