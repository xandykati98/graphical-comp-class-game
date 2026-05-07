Relatório Trabalho Prático G1
Nomes: Alexandre dos Santos, Vinícius Amorim

1. Descrição do jogo
O projeto é um jogo de puzzle baseado no Sokoban, ambientado em uma grade 2D. O jogador controla um slime que se move nas quatro direções (WASD) e pode empurrar caixas. O objetivo é posicionar todas as caixas sobre as células do tipo GOAL. O jogo inclui dois pisos especiais: ao pisar em um ROTATE_PAD, o jogador é teleportado para uma posição rotacionada 90° no sentido horário ao redor do centro do mapa; ao pisar em um SCALE_TOGGLE, o atributo size do jogador alterna entre 1 e 2, modificando sua área de ocupação. O número de movimentos é limitado por movements_left, e o jogador pode reiniciar a fase (R) ou avançar para a próxima ao vencer apertando N ou esperando um timer de 2 segundos.

2. Sistema de Referência do Universo (SRU)
O mundo é representado por uma instância de Grid, cujos atributos width e height armazenam, respectivamente, o número de linhas e de colunas da grade. A célula superior esquerda tem índice (0, 0): o eixo de linhas cresce para baixo e o de colunas, para a direita. Cada célula corresponde a um quadrado de cell_size = 50 pixels. A conversão para coordenadas de tela é direta: x = col * cell_size, y = row * cell_size. Essa correspondência é estabelecida pela projeção ortográfica configurada em reshape_window via glOrtho(0, width, height, 0, ...), com origem no canto superior esquerdo e Y crescendo para baixo.

3. Modelagem dos objetos e seus SROs
Cada objeto é desenhado com primitivas OpenGL (GL_QUADS, GL_TRIANGLES, GL_TRIANGLE_STRIP) a partir de vértices definidos explicitamente.

3.1. Player (Slime) 
O slime é definido com origem no canto superior esquerdo da sua célula de ancoragem. O tamanho total é size = scale * cell_size, onde scale é o atributo size do objeto Player, 1 ou 2. O corpo é um retângulo verde (GL_QUADS) que preenche toda a área do SRO. Dois olhos pretos quadrados são posicionados simetricamente: o esquerdo centrado em (0.2·size, 0.6·size) e o direito em (0.8·size, 0.6·size), cada um com lado 0.1 * size. O mapeamento para o SRU é feito transladando o SRO para (col * cell_size, row * cell_size), onde (row, col) é obtido de player.position.x e player.position.y. Quando size = 2, o retângulo cobre quatro células.

3.2. Box (Caixa) 
A caixa é modelada com origem no canto superior esquerdo da célula. O corpo principal é um retângulo laranja-marrom com margem de 0.02 * cell_size em todos os lados, definindo os limites left, right, top e bottom. Quatro bordas escuras (border = 0.1 * (cell_size - 2*margin)) são desenhadas nas extremidades internas. Três listras verticais escuras são distribuídas nos offsets 25%, 50% e 75% da largura interna, com espessura stripe = 0.1 * (cell_size - 2*margin). O mapeamento é feito por translação simples para (col * cell_size, row * cell_size)
.
3.3. Goal (Objetivo) 
O goal é composto por dois elementos. Primeiro, um fundo vermelho escuro é desenhado diretamente em draw_scene com glRectf. Em seguida, draw_goal desenha um quadrado vermelho vivo com recuo de pad = 0.1 * cell_size em cada lado, usando glRectf. O mapeamento é por translação para a célula correspondente.

3.4. Wall (Parede) - draw_wall(row, col)
A parede é formada por um retângulo de base cinza claro e linhas de argamassa cinza escuro. A espessura da argamassa é mt = max(2.0, 0.07 * cell_size). São desenhadas: uma linha de argamassa no topo da célula, uma linha horizontal central em mid_y = y + cell_size / 2.0, uma junta vertical a 50% da largura na metade superior, e duas juntas a 25% e 75% na metade inferior, formando o padrão de tijolos alternados. O mapeamento é por translação simples.

3.5. Scale Pad 
O piso de escala exibe dois quadrados concêntricos. O externo (azul escuro) preenche toda a célula. O interno (azul claro) tem margem de 0.25 * cell_size em cada lado, calculada pelas variáveis left, right, top e bottom. Ambos são desenhados com GL_QUADS. O mapeamento é por translação para (col * cell_size, row * cell_size).

3.6. Rotate Pad 
O piso de rotação é desenhado com centro em (cx, cy) = (col * cell_size + cell_size/2, row * cell_size + cell_size/2). O arco ciano de 270° é gerado com GL_TRIANGLE_STRIP entre o raio externo r_outer = 0.38 * cell_size e o interno r_inner = 0.22 * cell_size, de angle_start = 120° até angle_end = 390°, com 40 segmentos. A seta é um triângulo (GL_TRIANGLES) calculado na extremidade do arco a partir do vetor tangente (tx, ty) e do vetor radial normal (nx, ny), com comprimento tip_len = 0.17 * cell_size e meia-largura half_w = (r_outer - r_inner) * 0.95.

4. Transformações geométricas controladas pelo usuário
O movimento do jogador via WASD é mapeado em MOVE_DELTAS para deltas (dx, dy) aplicados a player.position.x e player.position.y. A lógica de colisão e empurre de caixas é centralizada em try_step, com try_move_giant tratando o caso size = 2. A escala é aplicada diretamente na geometria de draw_player: o parâmetro scale multiplica cell_size, expandindo o retângulo para cobrir quatro células sem alterar a matriz de projeção. A rotação de posição é calculada em apply_rotation, reposicionando o jogador via nova atribuição a player.position.x e player.position.y, com a flag just_rotated evitando ativações repetidas.