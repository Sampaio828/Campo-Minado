# Campo Minado

> Trabalho desenvolvido para o 2º Semestre do curso de Engenharia da Computação.

Um jogo de Campo Minado desenvolvido em Python utilizando a biblioteca **Pygame**, com suporte a temas visuais customizáveis, animações e sistema de pontuação.

---

## 1 - Pré-requisitos

O projeto requer **Python 3.10** ou superior e a biblioteca **Pygame**.

Para verificar a versão atual do seu Python, execute no terminal:
```bash
python --version
```

Instale as dependências:
   ```bash
   pip install pygame
   ```
---

## 2 - Como Executar o Jogo


2.1. **Execute o script principal:**
   ```bash
   python campo_minado.py
   ```

---

## 3 - Controles

| Ação | Comando |
| :--- | :--- |
| **Revelar célula** | `Clique Esquerdo` |
| **Marcar / Desmarcar bandeira** | `Clique Direito` ou tecla `F` |
| **Nova partida** | Tecla `R` |
| **Voltar ao menu / Sair** | Tecla `ESC` |

---

## 4 - Mapa da Arquitetura do Código

O código-fonte está organizado nas seguintes seções funcionais:

4.1. **Constantes, Temas e Dificuldades:** Definição das configurações globais, resoluções e matrizes de cores.
4.2. **Modificadores:** Sistema de registro e aplicação de regras/modificadores de jogo (`aplicar_modificadores`).
4.3. **Lógica do Tabuleiro:** Matrizes de dados, geração de minas, algoritmo de revelação em cascata, marcação e verificação de vitória.
4.4. **Fim de Jogo:** Animações de derrota/vitória (`animar_derrota`, `animar_vitoria`), cálculo de pontuação e persistência de recordes.
4.5. **Renderização / Desenho:** Primitivas gráficas, renderização do tabuleiro, HUD, menus e pop-ups.
4.6. **Fluxo do Jogo e Eventos:** Loop principal da aplicação e tratamento de inputs utilizando sintaxe `match-case`.

---

## 5 - Licença

Este projeto foi desenvolvido estritamente para fins acadêmicos.
