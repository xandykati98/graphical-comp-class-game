# Relatório – Trabalho Prático G1: Jogo Pedagógico
**Título:** T1-CG-jogo1  
**Arquivo fonte:** jogo1-cg-t1.py  
**Disciplina:** Computação Gráfica  
**Data:** 07/05/2026

---

## 1. Descrição do Jogo

O jogo implementado é inspirado no clássico **Sokoban**, um quebra-cabeça de lógica onde o agente (jogador) deve empurrar caixas até as células-meta dentro de um mapa em grade. A dinâmica pedagógica está nas células especiais **Rotate Pad** e **Scale Toggle**, que introduzem transformações geométricas como mecânica de jogo: ao pisar em um Rotate Pad, o jogador tem sua posição rotacionada 90° em torno do centro do mapa; ao pisar em um Scale Toggle, a escala do agente seria alterada.

O jogo foi implementado com **PyOpenGL** (biblioteca GLUT + GL), projeção ortográfica 2D e entrada via teclado (teclas WASD).

---

## 2. Modelagem dos Objetos

O mundo do jogo é representado por uma **grade 2D** (matriz inteira) carregada de um arquivo `map.json`. Cada célula armazena um código inteiro:

| Código | Tipo de célula     |
|--------|--------------------|
| 0      | Vazio (Empty)      |
| 1      | Parede (Wall)      |
| 2      | Meta (Goal)        |
| 3      | Scale Toggle       |
| 4      | Rotate Pad         |

Além da grade estática, os seguintes objetos dinâmicos existem em tempo de execução:

| Objeto        | Cor (RGB normalizado) | Descrição                                         |
|---------------|-----------------------|---------------------------------------------------|
| Agente        | (0.2, 0.9, 0.2) verde | Controlado pelo jogador via WASD                  |
| Caixa         | (0.8, 0.5, 0.0) laranja | Empurrada pelo agente na mesma direção do movimento |
| Meta          | (1.0, 0.0, 0.0) vermelho | Célula estática; caixa sobre ela fica marrom escuro |
| Parede        | (0.5, 0.5, 0.5) cinza  | Obstáculo intransponível                          |
| Scale Toggle  | (0.0, 0.0, 1.0) azul  | Célula especial de escala (definida, não implementada) |
| Rotate Pad    | (0.0, 1.0, 1.0) ciano | Célula especial: rotaciona a posição do agente 90° |

Cada objeto dinâmico (agente e caixas) possui uma posição `(row, col)` em coordenadas de grade.

---

## 3. SRO – Sistema de Referência do Objeto

### 3.1 Sistema de Referência Global (tela)

A projeção utilizada é **ortográfica 2D** configurada via `glOrtho`:

```
glOrtho(0, largura_janela, altura_janela, 0, -1, 1)
```

- Origem em **pixel (0, 0) = canto superior esquerdo** da janela.
- Eixo **X** cresce para a direita (colunas da grade).
- Eixo **Y** cresce para baixo (linhas da grade).
- Unidade: 1 unidade de mundo = 1 pixel.

O tamanho da janela é ajustado automaticamente para `num_colunas × cell_size` por `num_linhas × cell_size` pixels (cell_size = 50 px).

---

### 3.2 SRO da Grade (Grid)

A grade é o objeto base. Seu SRO coincide com o sistema global:

- Célula `(row, col)` ocupa o retângulo de pixels:
  - `x_min = col × cell_size`
  - `y_min = row × cell_size`
  - `x_max = (col + 1) × cell_size`
  - `y_max = (row + 1) × cell_size`

A célula `(0, 0)` fica no canto **superior esquerdo** da janela.

---

### 3.3 SRO do Agente (Player)

- Representado como um quadrado de `cell_size × cell_size` pixels.
- Posição lógica armazenada em coordenadas de grade: `(player.x, player.y)` onde `x = row`, `y = col`.
- Posição no espaço de tela:
  - `x_pixel = player.y × cell_size` (coluna → espaço horizontal)
  - `y_pixel = player.x × cell_size` (linha → espaço vertical)
- **Origem local** do objeto: canto superior esquerdo da célula que ele ocupa.

---

### 3.4 SRO da Caixa (Box)

- Mesmo sistema do agente: posição lógica `(box.x, box.y)` em coordenadas de grade.
- Mapeamento para pixels idêntico ao do agente.
- **Origem local**: canto superior esquerdo da célula ocupada.

---

### 3.5 SRO das Células Especiais (Rotate Pad / Scale Toggle)

- São células estáticas da grade; seu SRO é o mesmo da grade.
- Não possuem estado próprio, apenas alteram o estado do agente ao contato.

---

## 4. Transformações Geométricas Implementadas

### 4.1 Translação

O agente se move pressionando **W / A / S / D**. Cada tecla aplica um delta `(dx, dy)` à posição em grade:

| Tecla | dx (linha) | dy (coluna) | Direção visual |
|-------|------------|-------------|----------------|
| W     | -1         | 0           | Cima           |
| S     | +1         | 0           | Baixo          |
| A     | 0          | -1          | Esquerda       |
| D     | 0          | +1          | Direita        |

A translação verifica colisão com paredes e limites do mapa antes de ser aplicada. Se uma caixa está no caminho, verifica se a célula além dela está livre; em caso afirmativo, a caixa também é transladada (empurrada).

Em coordenadas de tela, a nova posição em pixels é simplesmente `nova_posição_grade × cell_size`.

### 4.2 Rotação

Ao pisar em um **Rotate Pad** (célula cyan), a posição do agente é rotacionada **90° no sentido horário** em torno do **centro geométrico** da grade.

Fórmula aplicada (rotação 2D discreta sobre grade):

```
center_row = (num_rows - 1) / 2
center_col = (num_cols - 1) / 2

new_row = center_row + (old_col - center_col)
new_col = center_col - (old_row - center_row)
```

Esta operação é equivalente à rotação matricial:

```
[new_row]   [ 0   1 ] [old_row - center_row]   [center_row]
[new_col] = [-1   0 ] [old_col - center_col] + [center_col]
```

A rotação é bloqueada caso a célula destino seja uma parede ou limite do mapa. O flag `just_rotated` evita aplicações múltiplas enquanto o agente permanece sobre o pad.

### 4.3 Escala (Scale Toggle)

A célula **Scale Toggle** (azul) está definida no código e mapeada no sistema de células, mas a transformação de escala ainda não foi implementada (marcada com `pass`). A estrutura está preparada para aplicar uma mudança de escala visual ao agente ao pisar nessa célula.

---

## 5. Controles

| Tecla | Ação                              |
|-------|-----------------------------------|
| W     | Mover agente para cima            |
| S     | Mover agente para baixo           |
| A     | Mover agente para a esquerda      |
| D     | Mover agente para a direita       |

Não há suporte a mouse nesta versão.

---

## 6. Objetivo e Condição de Vitória

O agente deve empurrar **todas as caixas** (laranja) sobre as **células-meta** (vermelho). Quando isso ocorre, a função `check_victory()` detecta que todas as caixas estão sobre metas (`BOX_ON_GOAL`) e exibe a mensagem **"Fase completa!"** no título da janela, desabilitando a entrada de teclado.

O jogo também registra um contador de movimentos restantes (`movements_left`), iniciado em 10.

---

## 7. Estrutura do Projeto

```
src/
  game/
    main.py                   # Código principal (OpenGL, lógica, callbacks)
    phases/
      001/
        map.json              # Mapa da fase 1: grade 7×7 com parede, meta, rotate pad e scale toggle
```

O mapa da fase 1 é uma grade 7×7 com borda de paredes, uma caixa em `(3,3)`, agente em `(1,1)`, meta em `(2,5)`, Rotate Pad em `(2,3)` e Scale Toggle em `(5,2)`.

---

## 8. Tecnologias Utilizadas

- **Python 3**
- **PyOpenGL** (OpenGL + GLUT) – renderização e janela
- **JSON** – definição dos mapas de fase
