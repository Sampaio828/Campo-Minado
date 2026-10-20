# **================= Campo Minado =================**


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

## 4 - Arquitetura do Código

| Seção | Módulo | Descrição / Responsabilidades |
| :---: | :--- | :--- |
| **4.1** | **Constantes e Temas** | Paletas de cores (`TEMAS`), configurações e dificuldades |
| **4.2** | **Modificadores** | Registro e aplicação de modificadores do jogo (`aplicar_modificadores`) |
| **4.3** | **Lógica do Tabuleiro** | Matrizes, geração do campo, algoritmo em cascata, marcação e vitória |
| **4.4** | **Fim de Jogo** | Animações (`animar_derrota`/`vitoria`), sistema de pontuação e recordes |
| **4.5** | **Interface (UI/Desenho)** | Primitivas visuais, renderização do tabuleiro, HUD, menus e pop-ups |
| **4.6** | **Loop Principal** | Tratamento de eventos (`match-case`) e fluxo de execução do Pygame |

---

## 5 - Licença

Este projeto foi desenvolvido estritamente para fins acadêmicos.
