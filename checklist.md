# JARVIS Portátil — Checklist de implementação

Marca com **[x]** as funcionalidades implementadas. Deixa por marcar as que continuam parciais ou pendentes e indica o que já existe. Os ensaios, os resultados anteriores e os cenários de aceitação estão no [checklist de testes](docs/CHECKLIST_TESTES.md).

## Fase 1 — Base técnica

### Funcionamento local e desempenho

- [x] Instalar o Ollama no portátil.
- [x] Configurar o Hermes Agent para usar o Ollama como fornecedor local.
- [x] Configurar o modelo inicial `qwen3:8b`.
- [x] Escolher e configurar um modelo com suporte a chamadas de ferramentas. Modelo escolhido: `qwen3:8b`.

### Extensões e manutenção

- [x] Criar um registo de ferramentas com nome, finalidade, argumentos e permissões visíveis para cada ferramenta. A listagem publica o esquema e a indicação de leitura através de MCP.
- [x] Ligar a ferramenta de listagem ao Hermes por MCP.
- [x] Adicionar um diagnóstico que identifique falhas de ligação ao Ollama e ao Hermes Agent, um modelo em falta e uma ferramenta de listagem indisponível ou não executada.

### Permissões e privacidade

- [x] Aplicar permissões por ferramenta e utilizador antes de executar uma chamada.
- [x] Restringir ferramentas de ficheiros às pastas autorizadas.
- [x] Guardar credenciais fora das conversas.
- [x] Registar o que o JARVIS executou, porquê e com que resultado, incluindo pedidos recusados e falhas.
- [x] Tratar instruções encontradas em sites, emails e PDFs como conteúdo externo.

## Fase 2 — MVP

O ditado inclui uma alternativa local Whisper para navegadores sem reconhecimento local nativo.

### Voz

- [x] Implementar Alt+Shift+D para iniciar e parar o ditado com o JARVIS em foco.
- [x] Implementar o botão **Ditar** para iniciar e parar a transcrição local em PT-PT e rever o texto antes de enviar.
- [x] Disponibilizar **Ouvir resposta**, dar preferência a uma voz local PT-PT e expor **Parar leitura** durante a reprodução.
- [ ] Executar comandos por voz a partir da transcrição. Depende da transcrição e das ferramentas registadas.
- [x] Enfileirar frases para leitura automática à medida que o Hermes envia a resposta.
- [x] Cancelar a fila de leitura e bloquear a leitura das frases seguintes da resposta em curso.
- [x] Reconhecer «cancela» durante um pedido e fechar a ligação ao Hermes.
- [x] Corrigir o último lembrete pendente com «afinal, daqui a 30 minutos» sem reiniciar a conversa.
- [x] Permitir alterar a voz local de leitura.
- [x] Permitir alterar a velocidade da leitura.
- [x] Permitir selecionar um microfone e passar a faixa selecionada ao reconhecimento local.
- [x] Abrir as definições de som do Windows a partir do JARVIS para escolher a saída de áudio.
- [x] Desativar **Ler respostas automaticamente** e receber a resposta por texto.

### Conversa

- [x] Manter o contexto entre perguntas sucessivas na mesma sessão.
- [x] Resolver referências como «esse ficheiro» e «a reunião de amanhã» quando o contexto identifica uma única opção. Depende da pesquisa de ficheiros ou da consulta da agenda.
- [x] Pedir esclarecimento quando duas opções correspondem ao pedido e aguardar a seleção antes de agir.
- [x] Alternar o idioma da resposta durante uma conversa quando o utilizador pedir.
- [x] Ajustar o nível de detalhe quando o utilizador pedir uma resposta mais curta ou mais completa.

### Windows e aplicações

- [x] Abrir aplicações Windows suportadas pelo nome.
- [x] Enviar um ficheiro de texto pelo caminho selecionado ao VS Code.
- [x] Encaminhar um endereço HTTP ou HTTPS para o navegador predefinido.
- [x] Alterar o volume do Windows e apresentar o nível resultante.
- [x] Mudar o dispositivo de áudio predefinido do Windows.

### Programação

- [x] Abrir o projeto certo a partir de um nome reconhecido. Pedir a pasta ou a seleção quando houver vários projetos com o mesmo nome.
- [x] Abrir o JARVIS Portátil no VS Code com «Jarvis, abre o meu projeto no VS Code» e informar quando o editor está indisponível.
- [x] Resolver outros projetos autorizados por nome ou seleção e encaminhar a pasta para o VS Code.

### Pesquisa pessoal

- [x] Encontrar ficheiros pelo nome no projeto JARVIS e apresentar pedidos para os abrir.
- [x] Encontrar ficheiros de texto pelo conteúdo no projeto JARVIS.
- [x] Estender a pesquisa por nome e conteúdo aos restantes projetos autorizados.
- [x] Encontrar as notas da última sessão de um projeto autorizado em `notes/AAAA-MM-DD/`, mostrando os ficheiros e a origem da data.

### Ficheiros e documentos

- [x] Criar um ficheiro no projeto JARVIS sem sobrescrever e devolver a sua localização.
- [x] Guardar o texto de uma nota enviada pelo chat.

### Agenda e tarefas

- [x] Consultar os compromissos do dia na agenda local do perfil.
- [ ] Consultar compromissos do dia em calendários externos ligados.
- [x] Consultar a disponibilidade num intervalo e apresentar os períodos livres.
- [x] Criar temporizadores com aviso ao terminar.
- [x] Criar um lembrete relativo no chat, mostrar a hora calculada e emitir um aviso com a página aberta.
- [x] Calcular a próxima ocorrência de uma hora absoluta para agendar um aviso.
- [x] Editar o último lembrete pendente e substituir o aviso anterior.
- [x] Cancelar o último lembrete pendente.

### Painel e acessibilidade

- [x] Apresentar um chat com entrada por texto e respostas legíveis.
- [x] Abrir o Jarvis normal no navegador com o atalho do Windows.
- [x] Apresentar o início e a conclusão de uma chamada real de ferramenta no painel de atividade do Hermes.
- [x] Abrir o painel H.O.L.O Hands a partir do Jarvis normal quando o submódulo está instalado.
- [x] Mostrar os estados do microfone no painel.
- [x] Mostrar a transcrição parcial durante a escuta com reconhecimento nativo compatível. Na alternativa Whisper, a transcrição aparece depois de parar.
- [x] Mostrar legendas ao início de cada trecho lido e ocultá-las no fim.
- [x] Mostrar **Cancelar pedido** durante a execução e fechar o fluxo de resposta ao cancelar.
- [x] Permitir usar o chat, a escuta e o botão **Parar** por teclado.

### Funcionamento local e desempenho

- [x] Mostrar erros de integrações externas no comando afetado e manter os comandos locais disponíveis.

## Fase 3 — Memória e rotinas

### Conversa

- [x] Guardar o histórico de uma sessão e reabrir a conversa com o contexto anterior após fechar o JARVIS.

### Memória

- [x] Guardar preferências e aplicá-las em conversas posteriores.
- [x] Guardar um contacto e recuperá-lo pelo nome.
- [x] Guardar um projeto e recuperar a pasta associada.
- [x] Guardar um nome de dispositivo e resolvê-lo num pedido posterior.
- [x] Guardar uma rotina com o nome escolhido e recuperá-la por esse nome.
- [x] Interpretar «lembra-te disto», guardar a informação indicada e mostrá-la no editor.
- [x] Interpretar «esquece isto» e remover a memória selecionada.
- [x] Pesquisar conversas anteriores e abrir a conversa onde aparece o resultado.
- [x] Identificar nas respostas se uma afirmação veio de uma memória guardada ou de uma dedução.
- [x] Mostrar a data e a origem de cada memória.
- [x] Editar uma memória e usar o valor atualizado nas consultas.
- [x] Apagar uma memória pelo editor e removê-la da pesquisa e das respostas.
- [x] Exportar as memórias num ficheiro legível, com a data e a origem dos registos.
- [x] Isolar as memórias e o histórico por perfil. Os perfis pertencem à mesma conta Windows.

### Pesquisa pessoal

- [x] Pesquisar texto em PDFs nas pastas autorizadas.
- [x] Pesquisar transcrições guardadas nas pastas autorizadas.
- [x] Indexar por OCR o texto de documentos digitalizados a pedido e pesquisar o texto extraído.
- [x] Resumir um documento encontrado e apresentar a ligação para o original.
- [x] Responder a perguntas com ligações para as fontes e páginas quando aplicável.
- [x] Atualizar o índice quando um ficheiro é criado, alterado, movido ou apagado.

### Windows e aplicações

- [x] Gerir janelas, incluindo mover, minimizar, maximizar e restaurar uma janela identificada.
- [x] Mover uma janela para o monitor indicado.
- [x] Ativar e consultar o modo de foco do Windows.
- [x] Consultar a bateria e apresentar a percentagem e o estado de carregamento.
- [x] Consultar o armazenamento e apresentar o espaço disponível na unidade pedida.
- [x] Fazer uma captura de ecrã e devolver o ficheiro criado.
- [x] Ler a seleção ativa a pedido e apresentar o texto selecionado.
- [x] Ler a área de transferência a pedido e exigir autorização antes da consulta.
- [x] Criar espaços de trabalho como «modo estudo» e «modo programação» com as aplicações, pastas e janelas correspondentes.

### Ficheiros e documentos

- [x] Renomear um ficheiro.
- [x] Mover um ficheiro e impedir sobrescrita.
- [x] Pré-visualizar uma reorganização de Downloads e aplicar apenas os movimentos aprovados.
- [x] Identificar duplicados por SHA-256 e apresentar os caminhos.
- [x] Comprimir os ficheiros selecionados.
- [x] Extrair um arquivo para a pasta escolhida.
- [x] Converter um ficheiro para o formato pedido.
- [x] Preparar cópias de segurança de ficheiros selecionados e permitir restaurá-los.

### Agenda e tarefas

- [x] Criar eventos com título, data e hora no calendário indicado.
- [x] Reagendar um evento.
- [x] Detetar conflitos antes de criar ou reagendar um evento e mostrar os compromissos que se sobrepõem.
- [x] Preparar a agenda do dia por ordem cronológica.
- [x] Criar tarefas recorrentes e calcular a próxima ocorrência após concluir a atual.
- [x] Criar lembretes associados a eventos e atualizá-los quando o evento é reagendado.
- [x] Reservar blocos de foco na agenda.
- [x] Configurar a antecedência de um aviso de compromisso.

### Vida prática

- [x] Adicionar, remover e marcar como comprados itens numa lista de compras e recuperar a lista na sessão seguinte.

### Rotinas e fluxos

- [x] Criar regras do tipo «quando acontecer X, faz Y».
- [x] Agendar o modo programação.
- [x] Adicionar condições às rotinas.
- [x] Pré-visualizar as etapas, os destinos e os efeitos previstos de uma rotina.
- [x] Executar uma rotina manualmente a partir do painel, independentemente do horário.
- [x] Mostrar o histórico da rotina com a hora, os passos executados e o resultado.
- [x] Configurar «bom dia» para preparar a agenda e mostrar as tarefas do dia.
- [x] Configurar «modo programação» para ativar o espaço de trabalho escolhido e abrir as notas do projeto.
- [x] Configurar «fecha o dia» para rever o que ficou pendente e guardar uma nota de fecho.
- [x] Interpretar «faz como da última vez» e recuperar a rotina correspondente. Pedir esclarecimento se houver duas rotinas plausíveis.

### Painel e acessibilidade

- [x] Mostrar o histórico de conversas e permitir reabrir uma sessão.
- [x] Disponibilizar um editor para consultar, editar, apagar e exportar memórias. Depende das operações de memória.
- [x] Disponibilizar um editor para configurar, pré-visualizar e executar rotinas. Depende do motor de rotinas.

### Funcionamento local e desempenho

- [x] Consultar, editar e recuperar a memória local após reiniciar sem acesso externo.

### Extensões e manutenção

- [x] Criar cópias de segurança das definições, memórias e rotinas.
- [x] Restaurar uma cópia de segurança das definições, memórias e rotinas.

## Fase 4 — Tarefas em vários passos

Consulta os [comandos e dependências da Fase 4](README.md#comandos-da-fase-4).

### Conversa

- [x] Mostrar os passos planeados, em execução e concluídos de uma tarefa longa. **Implementado no painel do fluxo PDF → rascunho.**
- [x] Permitir que o utilizador intervenha numa tarefa longa para corrigir um ficheiro, destino ou outro parâmetro antes do passo que o utiliza. **Implementado para a escolha dos PDFs antes da comparação e a correção após falha.**

### Automatização de aplicações

- [ ] Navegar até ao ecrã ou recurso pedido numa aplicação integrada.
- [ ] Preencher um formulário e mostrar os valores para revisão. **Parcial. O painel preenche e mostra o rascunho local para revisão.**
- [ ] Transferir dados entre dois serviços autorizados com mapeamento dos campos.
- [ ] Gerar um ficheiro como resultado de uma sequência. **Parcial. O fluxo exporta o rascunho em TXT.**
- [ ] Executar sequências pela API ou por um atalho estável e verificar o resultado das ações importantes durante a execução. **Parcial. O fluxo PDF → rascunho usa a API local.**
- [ ] Automatizar ações pela interface visual quando a aplicação não tem integração e detetar o estado final das ações importantes.
- [x] Interromper a sequência se um resultado esperado não for confirmado e mostrar o passo que falhou. **Implementado no fluxo PDF → rascunho.**

### Ficheiros e documentos

- [x] Criar documentos DOCX e reler o conteúdo antes de guardar a versão final.
- [x] Editar parágrafos em documentos DOCX existentes e reler as alterações.
- [x] Criar folhas XLSX e reler os valores e fórmulas gravados.
- [x] Editar células e fórmulas em folhas XLSX existentes e reler as células gravadas. O recálculo depende de uma aplicação de folha de cálculo.
- [x] Criar apresentações PPTX com diapositivos de título e texto.
- [x] Editar títulos e campos de texto de conteúdo em apresentações PPTX existentes. A edição de conteúdo suporta diapositivos com um único campo de texto.
- [x] Comparar duas versões de um documento e indicar as diferenças e a respetiva localização. **Implementado para texto de PDF, DOCX, TXT e Markdown.**
- [x] Extrair tabelas de PDFs com texto e guardar em CSV.

### Pesquisa pessoal

- [ ] Pesquisar emails nas contas autorizadas e ligar os resultados às mensagens originais. Depende da autorização por conta.
- [x] Localizar as versões pedidas de um documento, compará-las e apresentar as diferenças com referências às duas origens. Depende da pesquisa e da comparação de documentos. **Implementado no fluxo PDF → rascunho com pesquisa por nome e seleção explícita.**

### Email e mensagens

- [ ] Ligar os serviços de email e mensagens usados pelo utilizador às contas autorizadas.
- [ ] Pesquisar uma conversa por contacto, assunto ou conteúdo.
- [ ] Resumir uma conversa e ligar às mensagens que sustentam o resumo.
- [ ] Destacar as perguntas que ainda aguardam resposta.
- [ ] Extrair tarefas mencionadas em mensagens e mostrar as respetivas origens.
- [ ] Extrair datas mencionadas em mensagens e pedir esclarecimento quando forem ambíguas.
- [x] Gerar, editar e guardar um rascunho local de email a partir da comparação de PDFs e permitir descarregá-lo em TXT.
- [ ] Redigir uma resposta a partir de uma conversa do serviço de email e mostrar o rascunho para revisão.
- [x] Selecionar ficheiros do projeto como anexos de um rascunho local, rever nomes e versões e exportar o email em EML. O JARVIS pede nova revisão se um ficheiro mudar.
- [ ] Associar os anexos revistos à mensagem a enviar no serviço de email ligado.
- [x] Mostrar e permitir editar o destinatário, o assunto e o conteúdo no rascunho local.
- [ ] Mostrar destinatários, assunto, conteúdo e anexos da versão que será enviada antes de pedir confirmação.
- [ ] Enviar a versão confirmada e guardar a referência do envio. Depende da pré-visualização e da confirmação.
- [ ] Responder por voz, permitindo rever a transcrição, o rascunho e o destinatário antes de confirmar. Depende da transcrição e da pré-visualização.
- [ ] Responder a «já enviaste o email?» consultando o estado no serviço ou na pasta de enviados.
- [ ] Permitir cancelar um envio antes da confirmação.

### Reuniões

- [ ] Preparar notas para uma reunião com ligações para os documentos relevantes.
- [ ] Transcrever reuniões após obter consentimento e parar a captura ao terminar a transcrição.
- [ ] Identificar as decisões tomadas na transcrição.
- [ ] Extrair tarefas da reunião com responsáveis e prazos quando estes forem indicados.
- [ ] Gerar um resumo com marcas temporais que permitem localizar os excertos relevantes.
- [ ] Preparar uma mensagem de seguimento a partir das decisões e tarefas.
- [ ] Associar as notas, a transcrição e o seguimento ao evento ou projeto correto.

### Internet e investigação

- [ ] Pesquisar na web e listar resultados que respondem ao pedido.
- [ ] Abrir as fontes selecionadas e consultar o conteúdo na origem.
- [ ] Comparar resultados de várias fontes e indicar onde concordam ou divergem.
- [ ] Distinguir factos atribuídos a fontes de inferências do JARVIS.
- [ ] Consultar a meteorologia para o lugar e o momento pedidos e mostrar a origem.
- [ ] Consultar o trânsito para o trajeto indicado e mostrar a hora da informação.
- [ ] Consultar horários de transportes para a data e o percurso pedidos.
- [ ] Consultar preços e indicar a moeda, a data e a fonte.
- [ ] Consultar notícias sobre um tema e indicar a data e a fonte.
- [ ] Guardar uma pesquisa com a pergunta, os resultados e as respetivas ligações.
- [ ] Preparar um relatório com ligações para as fontes usadas em cada conclusão.

### Programação

- [x] Pesquisar código no projeto autorizado e devolver os ficheiros e linhas relevantes. **Implementado com pesquisa literal e resultados por ficheiro e linha.**
- [ ] Explicar um erro usando a mensagem e o trecho de código relacionados.
- [x] Preparar uma proposta de alteração para os ficheiros autorizados e mostrar as diferenças para revisão. **Implementado para uma substituição textual localizada num ficheiro.**
- [x] Aplicar a proposta após aprovação e mostrar os ficheiros alterados. Se um ficheiro tiver mudado desde a revisão, pedir nova revisão antes de aplicar. **Implementado com aprovação por número e verificação da versão do ficheiro.**
- [ ] Correr os testes relevantes e apresentar os resultados, incluindo eventuais falhas.
- [x] Consultar o estado, o histórico ou o ramo do Git conforme o pedido. **Implementado.**
- [ ] Resumir um diff e indicar as alterações principais e os ficheiros afetados. **Parcial. Mostra estatísticas por ficheiro das alterações preparadas e por preparar.**
- [ ] Preparar um pull request com título, descrição e resultados dos testes para revisão.
- [ ] Executar código em ambiente isolado com limites de acesso ao projeto.

### Estudo e trabalho

- [ ] Explicar um tópico com exemplos adequados ao nível pedido.
- [ ] Criar cartões de estudo a partir da matéria indicada.
- [ ] Gerar um teste sobre os tópicos escolhidos.
- [ ] Corrigir respostas e explicar como chegar à solução.
- [ ] Registar os tópicos em que o utilizador teve dificuldades e recuperá-los na sessão seguinte.
- [ ] Gerar um plano de estudo que tenha em conta os tópicos, o tempo disponível e a data de avaliação.
- [ ] Preparar um documento a partir de materiais autorizados e indicar os materiais usados.
- [x] Acompanhar o progresso de um projeto e mostrar tarefas concluídas, pendentes e próximos prazos. **Implementado a partir do checklist Markdown de um projeto autorizado. Os prazos vêm das datas explícitas nas tarefas.**

### Vida prática

- [ ] Sugerir receitas a partir dos ingredientes disponíveis e distinguir os que ainda é preciso comprar.
- [ ] Planear refeições para os dias escolhidos e gerar a lista de ingredientes em falta.
- [ ] Preparar um plano de viagem com as datas, locais e opções de transporte pedidas.
- [x] Registar itens e quantidades no inventário doméstico por perfil e recuperá-los por nome ou localização.
- [x] Catalogar recibos PDF do projeto por data e comerciante e abrir os originais a partir da pesquisa.
- [x] Registar despesas em euros, anulá-las por número e apresentar totais por período e categoria.
- [ ] Preparar um carrinho e mostrar os artigos, as quantidades e o total para aprovação.
- [ ] Preparar uma reserva e mostrar as opções, as datas e as condições para aprovação.
- [ ] Preparar um formulário e mostrar os dados preenchidos para aprovação antes da submissão.

### Rotinas e fluxos

- [x] Inserir uma etapa de aprovação que bloqueia o próximo passo até à decisão. Implementado para a confirmação dos PDFs.
- [x] Persistir o estado das tarefas em curso, incluindo passos concluídos, passo atual e aprovações pendentes, e retomar nesse ponto após reiniciar. Implementado no fluxo PDF → rascunho por perfil.
  - [x] Implementar o acompanhamento persistente de downloads e o aviso de conclusão no painel.
- [x] Permitir repetir apenas o passo em falta após uma falha e manter os passos concluídos registados. Implementado no fluxo PDF → rascunho.
- [ ] Evitar repetir ações com efeitos externos ao verificar o estado no serviço antes de uma nova tentativa.
- [x] Cancelar uma tarefa entre dois passos e mostrar o que já aconteceu e o que ficou por executar. **Implementado no painel do fluxo PDF → rascunho.**

### Painel e acessibilidade

- [x] Mostrar as ações pendentes com os detalhes necessários para aprovar ou recusar cada uma. **Implementado para a seleção de PDFs pendente de confirmação.**
- [x] Mostrar as tarefas em execução, o passo atual e os controlos disponíveis para intervir. **Implementado no painel do fluxo PDF → rascunho.**

### Permissões e privacidade

- [ ] Restringir o acesso às integrações por conta autorizada.
- [ ] Pedir confirmação antes de enviar mensagens. Depende de poder mostrar os destinatários, o conteúdo e os anexos.
- [ ] Pedir confirmação antes de efetuar compras. Depende de poder mostrar o vendedor, os artigos e o total.
- [ ] Pedir confirmação antes de eliminar ficheiros permanentemente. Depende de poder identificar os ficheiros e mostrar o efeito da eliminação.
- [ ] Invalidar a confirmação quando o conteúdo ou destino da ação muda e pedir nova confirmação.

### Extensões e manutenção

- [ ] Integrar uma ferramenta por MCP e aplicar as permissões registadas.
- [ ] Instalar extensões e publicar as ferramentas permitidas no registo.
- [ ] Desativar extensões e bloquear chamadas às respetivas ferramentas.
- [ ] Verificar as ligações às integrações e identificar serviços indisponíveis no painel.
- [ ] Recuperar tarefas após uma falha e reconciliar os efeitos externos já confirmados. **Parcial. O fluxo PDF → rascunho retoma passos locais.**

## Fase 5 — Versão avançada

### Programação

- [ ] Criar uma extensão opcional do VS Code para mostrar a seleção ou o ficheiro ativo antes de o enviar ao JARVIS.
- [ ] Mostrar a proposta do JARVIS como uma comparação dentro do VS Code e permitir aprová-la ou descartá-la. Depende da geração e aplicação de propostas da Fase 4.

### Voz

- [ ] Ativar a transcrição com «Olá, Jarvis». Depende da transcrição e da indicação do estado do microfone.

### Ecrã, imagens e câmara

- [ ] Interpretar uma captura de ecrã fornecida pelo utilizador e explicar o que nela aparece.
- [ ] Interpretar a janela ativa a pedido e identificar a aplicação e o conteúdo visível.
- [ ] Ler uma mensagem de erro no ecrã e reproduzir o texto relevante.
- [ ] Identificar o botão referido pelo utilizador numa captura ou janela.
- [ ] Extrair dados de uma imagem e permitir que sejam revistos.
- [ ] Partilhar uma janela temporariamente para acompanhamento em direto e parar a captura ao terminar a partilha.
- [ ] Digitalizar um documento com a câmara após ativação explícita e devolver a imagem ou o texto extraído.
- [ ] Interpretar uma imagem da câmara após ativação explícita e desativar a captura quando a operação termina.

### Internet e investigação

- [ ] Vigiar alterações numa página indicada e mostrar o que mudou desde a última verificação. Depende da pesquisa web e das rotinas agendadas.

### Casa inteligente

- [ ] Ligar o Home Assistant ou os serviços dos dispositivos e apresentar os dispositivos autorizados.
- [ ] Controlar luzes e apresentar o estado final reportado.
- [ ] Controlar tomadas e apresentar o estado final reportado.
- [ ] Controlar estores e apresentar a posição final reportada.
- [ ] Ajustar a climatização e apresentar a temperatura alvo ou o modo definido.
- [ ] Controlar a reprodução de música através da integração da casa e apresentar o estado do dispositivo.
- [ ] Controlar o aspirador e apresentar o estado reportado.
- [ ] Consultar os sensores da divisão pedida e mostrar a leitura e a hora.
- [ ] Consultar consumos e apresentar os valores para o dispositivo e o período pedidos.
- [ ] Criar e ativar cenas por divisão e apresentar o estado de cada dispositivo após ativação.
- [ ] Agendar a ativação de uma cena por hora.
- [ ] Mostrar quando um dispositivo não confirmou a mudança e apresentar o último estado conhecido.

### Música e entretenimento

- [ ] Reproduzir a música encontrada no serviço escolhido.
- [ ] Reproduzir o episódio de um podcast selecionado.
- [ ] Reproduzir um vídeo selecionado.
- [ ] Gerir a fila de reprodução, permitindo adicionar, remover e mover itens.
- [ ] Consultar e controlar o que está a tocar na divisão indicada.
- [ ] Ajustar o volume da reprodução na divisão escolhida e apresentar o nível resultante.
- [ ] Retomar um episódio na posição guardada.
- [ ] Encontrar uma música pela descrição e apresentar as correspondências.
- [ ] Encontrar um filme ou uma série pela descrição e apresentar as correspondências.

### Telemóvel e acesso remoto

- [ ] Enviar pedidos por chat no telemóvel e receber a resposta.
- [ ] Usar voz no telemóvel com transcrição e resposta falada.
- [ ] Receber notificações com uma ação rápida no telemóvel e aplicar a ação à tarefa associada.
- [ ] Sincronizar alterações de tarefas entre PC e telemóvel.
- [ ] Enviar fotografias do telemóvel para uma pasta de destino no PC.
- [ ] Enviar documentos do telemóvel para o PC.
- [ ] Consultar no telemóvel o estado das automações a correr no PC.
- [ ] Suspender remotamente uma tarefa iniciada noutro dispositivo e bloquear a execução da etapa seguinte enquanto está suspensa.
- [ ] Cancelar remotamente uma tarefa e mostrar o resultado nos dois dispositivos.

### Conversa

- [ ] Retomar no telemóvel uma conversa do PC preservando contexto e perfil. Depende da sincronização e do histórico.

### Agenda e tarefas

- [ ] Criar lembretes por localização com acesso autorizado. Depende das notificações no telemóvel.

### Proatividade

- [ ] Entregar um briefing da manhã à hora definida, com a agenda e as tarefas relevantes.
- [ ] Alertar quando surge um conflito na agenda e mostrar os eventos envolvidos.
- [ ] Avisar de um prazo com a antecedência configurada.
- [ ] Alertar quando um serviço monitorizado falha e indicar qual deixou de responder.
- [ ] Notificar o utilizador quando se cumpre uma condição que pediu para vigiar, com uma ligação ou referência ao resultado.
- [ ] Aplicar horas de silêncio e manter pendentes os avisos sem permissão para interromper.
- [ ] Agrupar notificações relacionadas mantendo cada evento identificável.
- [ ] Configurar que tipos de alerta podem interromper o utilizador.

### Painel e acessibilidade

- [ ] Configurar um controlo físico opcional para iniciar a escuta ou parar uma tarefa.

### Permissões e privacidade

- [ ] Aplicar permissões por dispositivo.
- [ ] Atribuir uma permissão própria a ações físicas sensíveis, como abrir uma porta.
- [ ] Mostrar o dispositivo e o efeito pretendido antes de confirmar uma ação física sensível.
- [ ] Permitir revogar a partilha de janela, câmara ou localização e terminar a recolha dependente.

### Funcionamento local e desempenho

- [ ] Encaminhar pedidos simples para um modelo rápido.
- [ ] Encaminhar tarefas longas para um modelo mais capaz.
- [ ] Ativar o modelo de visão quando o utilizador pede uma análise de imagem, janela ou câmara.
- [ ] Permitir ativar ou desativar serviços externos preservando os comandos locais.

## Protótipo H.O.L.O Hands

### Validar a base

- [ ] Inspecionar o fluxo de chat e voz do Jarvis para identificar por onde enviar contexto de um cartão e ler a resposta.

### Ligar o gesto ao modelo

- [x] Fixar a revisão do H.O.L.O usada no protótipo e preservar a licença e os créditos.
- [x] Reutilizar a ação de resumo do H.O.L.O para enviar a nota selecionada a uma rota local.
- [x] Implementar o resumo no Ollama e a apresentação do resultado no painel.
- [x] Mostrar o estado de processamento e tratar pedidos repetidos, Ollama indisponível e modelo em falta.

### Integrar a voz

- [x] Adicionar a leitura pelo navegador, com seleção de voz local e indicação de voz indisponível.
- [x] Usar a nota aberta como contexto de uma pergunta escrita.
- [x] Adicionar ditado local ao campo de pergunta.

### Preparar a instalação

- [ ] Documentar a configuração e o arranque no Windows, incluindo a instalação inicial dos modelos.
- [ ] Registar os passos para resolver problemas de câmara, microfone ou Ollama.
