# Campo-Minado
Trabalho para o 2° Semestre da faculdade de engenharia da computação.

=================================================
                   CAMPO MINADO
=================================================

Requer Python 3.10+ e Pygame, rode os seguintes comandos no seu CMD:

Instalar pygame:
    pip install pygame
		
Verificar versão do seu python:
    python --version
		
Executar o jogo:
        python campo_minado.py

--------------------------------------------------------------------------------------------------

CONTROLES:
    Clique esquerdo ........ revela a célula
    Clique direito / F ..... marca / desmarca bomba
    R ...................... nova partida
    ESC ... voltar

--------------------------------------------------------------------------------------------------

MAPA DO CÓDIGO:
    1. CONSTANTES, TEMAS (paletas) e DIFICULDADES
    2. MODIFICADORES (registro + aplicar_modificadores)
    3. LÓGICA DO TABULEIRO (matrizes, geração, cascata, marcação, vitória)
    4. FIM DE JOGO (animar_derrota / animar_vitoria / pontuação / recordes)
    5. DESENHO (primitivas, tabuleiro, HUD, menu, pop-up)
    6. EVENTOS / FLUXO (match-case) e LOOP PRINCIPAL
	
--------------------------------------------------------------------------------------------------
