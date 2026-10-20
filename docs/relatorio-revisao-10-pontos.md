# Revisão dos dez pontos de segurança

Data: 20/10/2026. Branch local: `feature/security-review-source-only`.
Repositório de destino: [sailpoint-oss/colab-SailPoint-IIQ-on-Docker](https://github.com/sailpoint-oss/colab-SailPoint-IIQ-on-Docker/).

Revisão baseada no pedido original de Danielle e na árvore atual do projeto, com as validações locais realizadas antes da consolidação dos fontes. A branch de publicação foi recriada a partir da main para não incluir o histórico antigo de binários/exports; veja a [auditoria de publicação](auditoria-publicacao.md).

**Situação:** os dez grupos obrigatórios receberam implementação. A troca da senha administrativa do IIQ está descrita como passo manual, mas não foi executada. A homologação funcional completa e a execução dos workflows no GitHub continuam pendentes. Implementação, teste técnico local e aceite funcional são indicados separadamente abaixo.

## 1. Senhas fixas

| Solicitado | O que foi feito | Situação / evidência |
| --- | --- | --- |
| Obrigatório: retirar senhas fixas dos arquivos, inclusive SQL, LDAP, formulário e `.env`. | `.env` ignorado; `.env.example` sem credenciais. SQL e LDAP exigem variáveis. SQLCMD recebe placeholders. Usuários de exemplo têm hashes com salt e senhas aleatórias descartadas. Formulário LDAP sem senha compartilhada. | Implementado. Renderização e rejeição de valores inválidos testadas; Gitleaks da árvore de fontes aprovado. |
| Obrigatório: exigir senhas únicas no README. | Instruções para contas distintas, arquivo local protegido e cinco valores codificados pelo IIQ. | Implementado no README. |
| Recomendado: incluir uma etapa inicial de troca da senha administrativa IIQ. | Passo manual no primeiro login, incluindo confirmação de que a senha antiga falha. | Documentado; **troca não executada**. O pedido não determina automação. Senhas SQL/LDAP não são a senha do administrador web. |
| Recomendado: secret scanning nos PRs. | Workflow com Gitleaks fixado por digest, regras gerais e específicas. | Implementado e varredura local aprovada. Workflow remoto ainda não executado nesta sessão. |

Os segredos antigos permanecem no histórico Git. Remoção da árvore atual não reescreve os commits; qualquer reutilização real requer rotação.

## 2. Exposição de rede

| Solicitado | O que foi feito | Situação / evidência |
| --- | --- | --- |
| Obrigatório: publicar portas somente em `127.0.0.1`. | Portas com `${BIND_ADDRESS:-127.0.0.1}`. | Configuração validada e publicações locais confirmadas no Docker. |
| Obrigatório: retirar a porta 9009. | Mapeamento removido. | Verificado na configuração. |
| Obrigatório: documentar opção explícita de acesso remoto. | `BIND_ADDRESS` para interface selecionada, com orientações de HTTPS/autenticação e alternativa por túnel SSH. | Implementado no README e guia operacional. |
| Recomendado: Mailpit autenticado ou restrito à máquina local. | UI e SMTP em loopback por padrão. | Atende pela restrição local; autenticação não está habilitada. A opção remota exige proteção adicional conforme documentação. |
| Recomendado: não publicar SQL Server. | Sem porta SQL no host, acesso pela rede Compose. | Verificado no Docker. |

## 3. Dependências

| Solicitado | O que foi feito | Situação / evidência |
| --- | --- | --- |
| Obrigatório: substituir `sqljdbc4.jar`, registrar versão/origem e preferir download no build. | JAR antigo removido. Microsoft JDBC 13.6.0.jre11 baixado do Maven Central e SHA-256 conferido no build. | Download/hash verificados; driver testado com o SQL local. |
| Obrigatório: atualizar Tomcat 9/JDK 21 e digest. | Base atualizada e fixada por digest nos estágios de build/runtime. | Imagem construída; Tomcat 9.0.123/JDK 21 utilizados na validação local. |
| Recomendado: SQL Server CU27. | Imagem SQL Server 2022 CU27. | Build e execução local aprovados. |
| Recomendado: automatizar atualizações de imagens e driver. | Dependabot para Docker/Compose, Actions e Python; workflow semanal próprio para driver, com verificação do JAR/hash e PR revisável. | Scripts testados localmente. PRs do bot dependem de publicação e permissão nas configurações do GitHub. Sem atualização ou merge automático de produção. |

Arquivos principais: `tomcat/Dockerfile`, `sqlserver_iiq/Dockerfile`, `.github/dependabot.yml`, `.github/workflows/update-jdbc.yml`, `scripts/update_jdbc.py`.

## 4. Segredos codificados na configuração IIQ

| Solicitado | O que foi feito | Situação / evidência |
| --- | --- | --- |
| Obrigatório: retirar valores `1:ACP:` dos templates e fornecer no build. | Tokens nos dois arquivos de propriedades; renderização por secret BuildKit a partir do `.env` local. | Testes com entrada válida/inválida aprovados e build real concluído. |
| Obrigatório: remover `PassphraseForPrivateKey` do HR se desnecessário. | Atributo removido de `Application-HumanResources.xml`. | Verificado na fonte. |
| Recomendado: senhas diferentes para as três contas IIQ e explicar `iiq encrypt`. | README inclui `identityiq`, `identityiqPlugin`, `identityiqah`, mapeamento das cinco senhas codificadas e exigência de mesma versão/chave IIQ. | Documentado; valores locais gerados com CLI licenciado. |

A imagem renderizada contém material sensível e deve permanecer privada. Alterações no secret de build exigem reconstrução sem cache.

## 5. Segurança das conexões LDAP e JDBC

| Solicitado | O que foi feito | Situação / evidência |
| --- | --- | --- |
| Obrigatório: certificado no slapd e `useSSL=true`. | LDAPS em 636, certificado inicial de sete dias, SAN `ldap` e confiança no Java. | Bootstrap, certificado, conexão LDAPS e reinício testados. |
| Obrigatório: bloquear leitura anônima e proteger `userPassword`. | ACLs no slapd; simple binds exigem TLS; listener plaintext desabilitado. | Testes negativos de leitura anônima, senha alheia e conexão plaintext aprovados. |
| Obrigatório: hashes no LDIF. | SSHA com salt individual e senhas aleatórias descartadas. | Formato/unicidade testados. |
| Recomendado: `encrypt=true` e validar certificado JDBC. | Quatro URLs com `trustServerCertificate=false`; certificado SQL com SAN `sqlserver`; CA pública em truststore Java/SQLCMD; SQL força TLS. | Conexão positiva com quatro logins, rejeição de CA desconhecida e hostname incorreto aprovadas. Aplicação JDBC persistida atualizada por import direcionado. |
| Recomendado: orientar substituição dos certificados ou gerar certificados curtos. | Geração no primeiro início e guia de substituição. SQL tem inicializador isolado e renovação avaliada no início; CA de 365 dias. LDAP tem renovação manual documentada. | Geração/conexão validadas. Operação com certificados próprios e planejamento de renovação exigem aceite do operador. Não há renovador contínuo. |

## 6. Endurecimento do Tomcat e dos containers

| Solicitado | O que foi feito | Situação / evidência |
| --- | --- | --- |
| Obrigatório: usuário não root e substituir permissões 777. | Tomcat/IIQ como UID/GID 10001, ownership específico e mounts graváveis delimitados. | Verificado na imagem e no runtime. |
| Obrigatório: build em etapas sem ferramentas do builder no runtime. | SSB, Ant e downloads no builder; ferramentas herdadas removidas do runtime. | Imagem construída e ferramentas conferidas na etapa de montagem. |
| Recomendado: desligar ferramentas SSB sem uso e explicar reativação. | Flags `deploy...` desabilitadas; guia de reativação seletiva e rebuild. | Conferido em `docker.build.properties`. |
| Recomendado: plugin SQL/import false por padrão. | `plugins.runSqlScripts=false` e `plugins.importObjects=false`. | Conferido no template. |
| Recomendado: limites e filesystem somente leitura. | Todos os serviços com raiz somente leitura e limites; volumes/tmpfs para áreas de escrita necessárias. | Configuração e runtime confirmados; SQL/LDAP bootstrap e reinício aprovados; IIQ inicia e volta após reinício. |

## 7. Licenciamento e o arquivo UIConfig

| Solicitado | O que foi feito | Situação / evidência |
| --- | --- | --- |
| Obrigatório: remover JAR legado e corrigir afirmação de ausência de conteúdo proprietário. | JAR removido; README explicita exemplos IIQ e termos dos artefatos licenciados. | Verificado. |
| Obrigatório: remover o export completo UIConfig se não necessário; caso contrário, consultar a equipe antes de publicar. | `tomcat/file_config/UI/UIConfig-Uiconfig.xml` removido e mantido ausente. | Validado conforme investigação abaixo. |
| Recomendado: NOTICE, EULA explícita e requisitos de licença. | NOTICE com componentes; `.env.example` sem aceite prévio; entrypoint exige `ACCEPT_EULA=Y`; README explica SQL/IIQ/SSB. | Implementado. Aceite local Developer recebido explicitamente do usuário. |

### O UIConfig é necessário para subir?

**Não é necessário para a subida da stack atual.** A conclusão se baseia nos seguintes fatos:

1. O arquivo histórico era um export do objeto `UIConfig`, com 777.080 bytes e 230 configurações principais: colunas, grids, telas de identidades, certificações e outros ajustes de interface. Não era o arquivo de configuração do Tomcat nem o schema do banco.
2. O produto licenciado já fornece um `UIConfig` em `WEB-INF/config/init-default_org.xml`. O export customizado não é idêntico a essa base; removê-lo não garante reproduzir eventuais preferências visuais do ambiente de origem.
3. O arquivo customizado não existe na aplicação construída e não aparece na lista gerada `sp.init-custom.xml`.
4. A base inicializada contém o objeto `UIConfig` em `identityiq.spt_uiconfig`; portanto, retirar o export do projeto não retirou a configuração padrão da interface do produto.
5. A instância foi montada sem esse export e `/identityiq/login.jsf` respondeu HTTP 200 com formulário de senha; o reinício também foi validado na etapa anterior.

Não há evidência suficiente para afirmar por que o export foi adicionado originalmente. Ele pode ter preservado ajustes de interface daquele ambiente, mas não deve ser mantido inteiro apenas por precaução. Se surgir uma necessidade visual concreta, identificar somente o ajuste necessário e revisar sua forma de distribuição com a equipe SailPoint. A validação atual cobre bootstrap/login, não equivalência de todas as telas.

## 8. Código das aplicações de exemplo (mock)

“Mock” é a aplicação de demonstração que simula um sistema integrado ao IIQ. Neste projeto, o banco `appMock` representa usuários, grupos e vínculos; as regras LDAP constroem os DNs usados no provisionamento. Os pedidos corrigem esse código de exemplo, não o código interno do produto IIQ.

| Solicitado | Problema / exemplo | O que foi feito | Evidência / limite |
| --- | --- | --- | --- |
| Obrigatório: escapar valores dos DNs de conta e grupo. | Um nome como `Doe, Jane` ou `x,ou=Admins` não pode virar parte da estrutura LDAP ao concatenar `cn=...`. | `javax.naming.ldap.Rdn.escapeValue` aplicado ao nome da identidade e aos dois caminhos do formulário de grupo, antes de compor o DN. | Novo teste executa as regras BeanShell construídas com vírgula, `+`, `#`, espaços, barra, aspas, `;`, `=`, NUL e tentativa de acrescentar outra OU. Confere valor do CN e limites da subárvore. Não equivale a provisionar esses nomes no LDAP. |
| Obrigatório: limitar o DELETE de grupos de `UPDATE_USER` ao usuário alvo. | Remover “Administrator” de A não pode remover esse vínculo também de B. | DELETE inclui `iduser = @idUser` junto ao filtro do grupo. | Regressão cria vínculo de outro usuário e verifica que somente o alvo perde o grupo. |
| Obrigatório: interromper `INSERT_USER` quando duplicado. | Detectar duplicata e continuar poderia inserir usuário ou vínculos indevidos. | `THROW 50001`, transação, rollback, locks na checagem, login único e `SCOPE_IDENTITY()` para os vínculos do registro correto. | Testadas duplicatas de nome e login, com contagem de usuários/vínculos inalterada; inserção válida também testada. |
| Obrigatório: salt/hash em vez de coluna de senha aberta. | Uma leitura do banco não deve revelar a senha original. | Coluna antiga substituída por `password_salt` e `password_hash`; `CRYPT_GEN_RANDOM(32)` para salt e `HASHBYTES('SHA2_512', ...)`. Troca gera novo salt/hash; fixtures não têm senha conhecida. | Testados hash da atualização, tamanhos e ausência de salts repetidos. Modelo específico de laboratório; não é recomendação de armazenamento de senhas para um produto de autenticação. |
| Recomendado: validar identidade no `getObjectSQL` ou usar parâmetros. | Texto da identidade não deve ser interpretado como SQL. | Confirmado que o conector IIQ 8.5p1 converte o template em `?` e faz `PreparedStatement.setString`. Mantida sintaxe correta e incluída regressão usando o XML construído. | Testes com contas, grupos e payloads de injeção aprovados. Revalidar ao atualizar o conector. |
| Recomendado: appMock sem db_owner, só permissões necessárias. | Conta usada pelo conector não precisa administrar banco nem ler tabelas diretamente. | `GRANT EXECUTE ON SCHEMA::dbo`; sem db_owner e sem SELECT direto. | Login appMock executa procedures; testes confirmam ausência de db_owner e SELECT. |

Arquivos: `tomcat/file_config/Rule/Rule-OpenldapSetAccountDn.xml`, `Rule-OpenldapSetGroupDn.xml`, `sqlserver_iiq/scripts/98-create_table_app_mock.sql`, `scripts/sql-regression.sql`, `tests/LdapDnProbe.java`, `tests/JdbcBindingProbe.java`.

Os scripts corrigidos inicializam volumes novos. A instalação local validada já foi preparada com as correções SQL; não se deve aplicar novamente o CREATE DATABASE em uma base existente. Outros ambientes antigos precisam de migração própria, inclusive para remover eventual coluna antiga de senha.

## 9. Documentação

| Solicitado | O que foi feito | Situação / evidência |
| --- | --- | --- |
| Obrigatório: consolidar runbook no README e excluir o arquivo pessoal. | Instalação no README; `README_luisfpadovani.md` removido. Manutenção detalhada em `docs/operations.md`, acessível pelo README. | Revisto nesta etapa. |
| Obrigatório: URL correta e `.env` em minúsculas. | Clone agora usa `https://github.com/sailpoint-oss/colab-SailPoint-IIQ-on-Docker.git`, conforme destino indicado pelo usuário; `.env` consistente. | Comandos e caminhos revisados. O remote local não foi alterado. |
| Recomendado: indicar uso apenas em laboratório e excluir imagem sem uso. | Escopo local expresso no início; `api-linter-output.png` removido na primeira etapa. | Conferido. |

README reorganizado em requisitos, instalação sequencial, primeiro acesso, segurança, persistência, testes, licenças e contribuição. O guia operacional preserva certificados, exclusão opcional de conectores, SQL customizado, ferramentas SSB e atualização de dependências.

## 10. Dados de exemplo

| Solicitado | O que foi feito | Situação / evidência |
| --- | --- | --- |
| Obrigatório: retirar o nome pessoal do CEO ou obter autorização para mantê-lo. | Nome pessoal substituído; fixtures atuais usam identidades fictícias geradas por Faker. | CSV/LDIF revisados, sem depender de autorização para publicar o nome pessoal. |
| Recomendado: gerador de dados fictícios e menção no README. | Faker fixado, seed reproduzível para identidades, e-mails `example.com` e relações consistentes entre CSV/LDIF/SQL. README inclui procedência e comando de manutenção. | Quatro testes Python cobrem os contratos do gerador e do updater. Geração não sobrescreve dados em volumes existentes. |

## Testes e aceite restante

A revisão repetiu os checks de configuração, probes do IIQ e regressões descartáveis SQL/LDAP. O novo teste de DN usa as regras reais por BeanShell; os testes de SQL usam o script corrigido em uma base descartável. Resultados aprovados nesta execução:

| Verificação | Resultado |
| --- | --- |
| `scripts/validate.py` | Aprovado: syntax, renderização, falhas esperadas, loopback, raiz somente leitura e URLs JDBC estritas. |
| Testes Python (`test_*.py`) | Sete testes aprovados: gerador/fixtures, atualização/checksum do driver e bloqueio de artefatos na árvore e histórico novo. |
| `scripts/check_iiq.py` | Aprovado: DN das regras BeanShell em 33 cenários (11 entradas × conta/grupo/fallback), binding nativo para conta/grupo e TLS JDBC com quatro logins e testes negativos. A identidade IIQ normaliza o nome; o teste compara o DN com o valor efetivamente entregue à regra. |
| `ACCEPT_EULA=Y scripts/integration.py` | Aprovado: SQL/LDAP descartáveis, bootstrap, permissões, regressões do ponto 8, TLS e reinício. Aceite local já autorizado pelo usuário; ambiente de teste removido ao final. |
| UIConfig | Export customizado ausente, sem import dependente; objeto padrão presente no banco; login dinâmico HTTP 200. |
| Documentação | Links relativos, caminhos e URL de clone conferidos; versão/hash do driver preservados para o updater. |
| Gitleaks e `git diff --check` | Árvore versionável sem vazamentos detectados e sem erros de whitespace. Não inclui certificação do histórico Git. |

Continuam sob responsabilidade do aceite:

- Executar a troca manual da senha administrativa IIQ e confirmar rejeição da senha antiga.
- Homologar agregações, correlação e provisionamento completos dos três conectores; incluir operações reais de conta/grupo e DNs especiais.
- Homologar certificados próprios e a operação de renovação.
- Publicar a branch/PR, conferir workflows remotos e permitir PRs do bot no GitHub.
- Revisar histórico Git e eventual rotação de segredos reutilizados antes da publicação.

Nenhum push, PR, alteração de remote ou publicação de artefatos faz parte desta revisão local.
