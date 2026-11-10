#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import math
import random
import sys
import time
from datetime import date
from pathlib import Path

if sys.version_info < (3, 10):
    sys.exit("Este jogo usa match-case: é necessário Python 3.10 ou superior.")

import pygame

# =============================================================================
# 1. CONSTANTES, TEMAS E DIFICULDADES
# =============================================================================
LARGURA, ALTURA = 450, 800          # janela em formato "celular" (escala automática)
FPS = 60

# Estados possíveis de cada célula (matriz jogo["estado"])
OCULTA, REVELADA, MARCADA = 0, 1, 2

try:
    ARQ_RECORDES = Path(__file__).with_name("recordes_campo_minado.json")
except NameError:                    # execução interativa
    ARQ_RECORDES = Path("recordes_campo_minado.json")

try:
    PASTA_ICONES = Path(__file__).with_name("assets") / "icons"
except NameError:
    PASTA_ICONES = Path("assets") / "icons"

# -----------------------------------------------------------------------------
# >>> PALETAS DE CORES  <<<
# Para criar um novo tema, basta adicionar uma entrada neste dicionário com
# as mesmas chaves. Ele aparece automaticamente no seletor de paletas.
#   fundo     : cor de fundo da tela e das células reveladas
#   celula    : cor de destaque (células ocultas, botões ativos, logo)
#   texto     : números, rótulos e ícones
#   texto_cel : cor de ícones desenhados sobre células ocultas (bombas/bandeiras)
#   linha     : contornos finos e divisórias
#   perigo    : célula da bomba que explodiu
# -----------------------------------------------------------------------------
TEMAS = {
    "Margarida": dict(
        fundo=(237, 237, 237),
        celula=(52, 58, 64),
        texto=(40, 44, 48),
        texto_cel=(242, 240, 235),
        linha=(195, 192, 185),
        perigo=(210, 50, 50),
    ),
    "Sálvia": dict(
        fundo=(46, 50, 44),
        celula=(162, 178, 138),
        texto=(240, 242, 236),
        texto_cel=(46, 50, 44),
        linha=(88, 95, 84),
        perigo=(200, 80, 60),
    ),
    "Oliva": dict(
        fundo=(32, 32, 30),
        celula=(160, 150, 100),
        texto=(236, 234, 220),
        texto_cel=(32, 32, 30),
        linha=(92, 92, 82),
        perigo=(180, 80, 50)
    ),
    "Esmeralda": dict(
        fundo=(38, 48, 44),
        celula=(72, 160, 122),
        texto=(235, 242, 238),
        texto_cel=(38, 48, 44),
        linha=(80, 98, 90),
        perigo=(210, 75, 75),
    ),
    "Oceano": dict(
        fundo=(34, 42, 54),
        celula=(92, 152, 212),
        texto=(236, 243, 250),
        texto_cel=(34, 42, 54),
        linha=(70, 85, 105),
        perigo=(215, 65, 80),
    ),
    "Neve": dict(
        fundo=(51, 51, 51),
        celula=(140, 170, 200),
        texto=(238, 238, 238),
        texto_cel=(51, 51, 51),
        linha=(100, 100, 100),
        perigo=(220, 100, 100)
    ),
    "Cobre": dict(
        fundo=(51, 51, 51),
        celula=(201, 132, 70),
        texto=(238, 238, 238),
        texto_cel=(51, 51, 51),
        linha=(100, 100, 100),
        perigo=(170, 62, 30),
    ),
    "Lavanda": dict(
        fundo=(42, 38, 52),
        celula=(158, 126, 204),
        texto=(242, 238, 248),
        texto_cel=(42, 38, 52),
        linha=(88, 78, 106),
        perigo=(220, 70, 120),
    ),
}
TEMA_PADRAO = "Margarida"

# -----------------------------------------------------------------------------
# DIFICULDADES  (a quantidade de bombas sorteada fica entre "min" e "max")
# Para criar outra: adicione aqui, inclua em ORDEM_DIF e em multiplicador_dificuldade().
# -----------------------------------------------------------------------------
DIFICULDADES = {
    "Fácil":   dict(cols=6, linhas=10, min=5,  max=10),
    "Média":   dict(cols=7, linhas=12, min=11,  max=19),
    "Difícil": dict(cols=8, linhas=14, min=20, max=30),   # maior proporção de bombas
}
ORDEM_DIF = ["Fácil", "Média", "Difícil"]


def multiplicador_dificuldade(nome):
    """Multiplicador de pontuação por dificuldade (usa match-case)."""
    match nome:
        case "Fácil":
            return 1.0
        case "Média":
            return 1.6
        case "Difícil":
            return 2.6
        case _:
            return 1.0


# =============================================================================
# 2. LÓGICA DO TABULEIRO
# =============================================================================
def agora():
    return time.monotonic()


def formatar_tempo(seg):
    seg = int(seg)
    return f"{seg}S" if seg < 60 else f"{seg // 60}:{seg % 60:02d}"


def criar_estado_jogo(dificuldade):
    """Cria o estado de uma partida. O tabuleiro só é gerado no 1º clique."""
    p = DIFICULDADES[dificuldade]
    cols, linhas = p["cols"], p["linhas"]
    jogo = {
        "dif": dificuldade, "cols": cols, "linhas": linhas,
        "n_bombas": random.randint(p["min"], p["max"]),
        # Matrizes (vetores 2D) que guardam todo o tabuleiro:
        "bombas":   [[False] * cols for _ in range(linhas)],   # há bomba?
        "vizinhas": [[0] * cols for _ in range(linhas)],       # nº de bombas ao redor
        "estado":   [[OCULTA] * cols for _ in range(linhas)],  # oculta/revelada/marcada
        "fase": "AGUARDANDO",       # AGUARDANDO > JOGANDO > ANIM_* > RESULTADO
        "inicio": 0.0, "fim": 0.0, "cliques": 0,
        "modo_bandeira": False,
        "estouradas": {}, "fila_estouros": [], "prox_estouro": 0.0,
        "intervalo": 0.15, "bomba_fatal": None, "ultimo_estouro": 0.0,
        "confetes": [], "t_fim_anim": 0.0, "resultado": None,
        "geo": calcular_geometria(cols, linhas),
    }
    return jogo


def calcular_geometria(cols, linhas):
    """Posição e tamanho do tabuleiro na tela -> (x0, y0, tamanho_celula)."""
    area_x, area_y, area_w, area_h = 20, 135, LARGURA - 40, ALTURA - 135 - 130
    tam = min(area_w // cols, area_h // linhas)
    x0 = (LARGURA - tam * cols) // 2
    y0 = area_y + (area_h - tam * linhas) // 2
    return x0, y0, tam


def vizinhos(jogo, l, c):
    for dl in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if (dl or dc) and 0 <= l + dl < jogo["linhas"] and 0 <= c + dc < jogo["cols"]:
                yield l + dl, c + dc


def gerar_tabuleiro(jogo, seguro_l, seguro_c):
    """Sorteia as bombas (random) evitando a célula clicada e seu entorno."""
    zona = {(seguro_l, seguro_c), *vizinhos(jogo, seguro_l, seguro_c)}
    todas = [(l, c) for l in range(jogo["linhas"]) for c in range(jogo["cols"])]
    candidatas = [p for p in todas if p not in zona]
    if len(candidatas) < jogo["n_bombas"]:           # tabuleiro pequeno demais
        candidatas = [p for p in todas if p != (seguro_l, seguro_c)]
    for l, c in random.sample(candidatas, jogo["n_bombas"]):
        jogo["bombas"][l][c] = True
    calcular_vizinhas(jogo)


def calcular_vizinhas(jogo):
    for l in range(jogo["linhas"]):
        for c in range(jogo["cols"]):
            jogo["vizinhas"][l][c] = sum(jogo["bombas"][a][b] for a, b in vizinhos(jogo, l, c))


def revelar_em_cascata(jogo, l, c):
    """Revela a célula; se for 0, expande (flood fill iterativo). Marcadas ficam protegidas."""
    pilha = [(l, c)]
    while pilha:
        a, b = pilha.pop()
        if jogo["estado"][a][b] != OCULTA or jogo["bombas"][a][b]:
            continue
        jogo["estado"][a][b] = REVELADA
        if jogo["vizinhas"][a][b] == 0:
            pilha.extend(vizinhos(jogo, a, b))


def marcar_celula(jogo, l, c):
    """Marca/desmarca célula suspeita (respeitando o limite máximo de bombas)."""
    if jogo["fase"] not in ("AGUARDANDO", "JOGANDO"):
        return
    match jogo["estado"][l][c]:
        case 0:   # OCULTA
            # Só permite marcar se ainda houver bombas disponíveis no contador
            if bombas_restantes(jogo) > 0:
                jogo["estado"][l][c] = MARCADA
        case 2:   # MARCADA
            # Desmarcar é sempre permitido para liberar bandeiras
            jogo["estado"][l][c] = OCULTA
        case _:
            pass


def bombas_restantes(jogo):
    marcadas = sum(row.count(MARCADA) for row in jogo["estado"])
    return jogo["n_bombas"] - marcadas


def verificar_vitoria(jogo):
    """Vitória = todas as células seguras reveladas."""
    for l in range(jogo["linhas"]):
        for c in range(jogo["cols"]):
            if not jogo["bombas"][l][c] and jogo["estado"][l][c] != REVELADA:
                return False
    return True


def processar_clique(jogo, l, c):
    """Clique esquerdo numa célula (respeita o modo bandeira e a proteção das marcadas)."""
    if jogo["fase"] not in ("AGUARDANDO", "JOGANDO"):
        return
    if jogo["modo_bandeira"]:
        marcar_celula(jogo, l, c)
        return
    if jogo["estado"][l][c] != OCULTA:               # marcada = protegida; revelada = ignora
        return
    if jogo["fase"] == "AGUARDANDO":                 # 1º clique nunca cai em bomba
        gerar_tabuleiro(jogo, l, c)
        jogo["fase"] = "JOGANDO"
        jogo["inicio"] = agora()
    jogo["cliques"] += 1

    if jogo["bombas"][l][c]:
        iniciar_derrota(jogo, (l, c))
        return
    revelar_em_cascata(jogo, l, c)
    if verificar_vitoria(jogo):
        iniciar_vitoria(jogo)


def tempo_decorrido(jogo):
    match jogo["fase"]:
        case "AGUARDANDO":
            return 0.0
        case "JOGANDO":
            return agora() - jogo["inicio"]
        case _:
            return jogo["fim"] - jogo["inicio"]


# =============================================================================
# 3. FIM DE JOGO: ANIMAÇÕES, PONTUAÇÃO E RECORDES
# =============================================================================
def iniciar_derrota(jogo, fatal):
    jogo["fase"] = "ANIM_DERROTA"
    jogo["fim"] = agora()
    jogo["bomba_fatal"] = fatal
    centro = fatal or ((jogo["linhas"] - 1) / 2, (jogo["cols"] - 1) / 2)
    bombas = [(l, c) for l in range(jogo["linhas"]) for c in range(jogo["cols"])
              if jogo["bombas"][l][c]]
    bombas.sort(key=lambda p: math.hypot(p[0] - centro[0], p[1] - centro[1]))
    jogo["fila_estouros"] = bombas                    # mais próximas primeiro (efeito cascata)
    jogo["intervalo"] = min(0.18, 1.8 / max(1, len(bombas)))
    jogo["prox_estouro"] = agora()


def animar_derrota(app, jogo, t):
    """Estoura as bombas sequencialmente; ao terminar abre o pop-up."""
    while jogo["fila_estouros"] and t >= jogo["prox_estouro"]:
        pos = jogo["fila_estouros"].pop(0)
        jogo["estouradas"][pos] = jogo["prox_estouro"]
        jogo["ultimo_estouro"] = jogo["prox_estouro"]
        jogo["prox_estouro"] += jogo["intervalo"]
    if not jogo["fila_estouros"] and t - jogo["ultimo_estouro"] > 0.9:
        finalizar_partida(app, jogo, vitoria=False)


def iniciar_vitoria(jogo):
    jogo["fase"] = "ANIM_VITORIA"
    jogo["fim"] = agora()
    jogo["t_fim_anim"] = agora() + 3.0


def animar_vitoria(app, jogo, t, dt):
    """Chuva suave de confetes durante ~3 s, depois abre o pop-up."""
    if t < jogo["t_fim_anim"] - 1.2:
        gerar_confetes(jogo, 2, app["tema"])
    atualizar_confetes(jogo, dt)
    if t >= jogo["t_fim_anim"]:
        finalizar_partida(app, jogo, vitoria=True)


def gerar_confetes(jogo, n, tema):
    cores = [tema["celula"], tema["texto"],
             misturar(tema["celula"], tema["texto"], 0.5),
             misturar(tema["celula"], tema["fundo"], 0.5)]
    for _ in range(n):
        jogo["confetes"].append(dict(
            x=random.uniform(0, LARGURA), y=random.uniform(-60, -10),
            vx=random.uniform(-20, 20), vy=random.uniform(90, 220),
            w=random.uniform(6, 12), h=random.uniform(4, 8),
            ang=random.uniform(0, 6.28), vang=random.uniform(-4, 4),
            fase=random.uniform(0, 6.28), cor=random.choice(cores)))


def atualizar_confetes(jogo, dt):
    for p in jogo["confetes"]:
        p["fase"] += dt * 3
        p["x"] += (p["vx"] + math.sin(p["fase"]) * 30) * dt     # balanço lateral
        p["y"] += p["vy"] * dt
        p["ang"] += p["vang"] * dt
    jogo["confetes"] = [p for p in jogo["confetes"] if p["y"] < ALTURA + 20]


def calcular_pontuacao(jogo, tempo, vitoria):
    seguras = sum(row.count(REVELADA) for row in jogo["estado"])
    base = seguras * 10 + (jogo["n_bombas"] * 50 if vitoria else 0)
    base -= int(tempo) * 2 + jogo["cliques"] * 3
    mult = multiplicador_dificuldade(jogo["dif"])
    return max(0, int(base * mult))


def carregar_recordes():
    try:
        return json.loads(ARQ_RECORDES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def salvar_recordes(recordes):
    try:
        ARQ_RECORDES.write_text(json.dumps(recordes, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def registrar_recorde(app, dif, pontos, tempo):
    """Insere no top 5 da dificuldade; retorna a posição (1..5) ou None."""
    lista = app["recordes"].setdefault(dif, [])
    novo = dict(pontos=pontos, tempo=int(tempo), data=date.today().isoformat())
    lista.append(novo)
    lista.sort(key=lambda r: r["pontos"], reverse=True)
    del lista[3:]
    salvar_recordes(app["recordes"])
    return next((i + 1 for i, r in enumerate(lista) if r is novo), None)


def finalizar_partida(app, jogo, vitoria):
    """Calcula o resultado uma única vez e abre o pop-up."""
    tempo = jogo["fim"] - jogo["inicio"]
    pontos = calcular_pontuacao(jogo, tempo, vitoria)
    melhor_antes = max((r["pontos"] for r in app["recordes"].get(jogo["dif"], [])), default=0)
    posicao = registrar_recorde(app, jogo["dif"], pontos, tempo) if vitoria and pontos > 0 else None
    jogo["resultado"] = dict(vitoria=vitoria, pontos=pontos, tempo=tempo, posicao=posicao,
                             melhor_antes=melhor_antes, cliques=jogo["cliques"])
    jogo["fase"] = "RESULTADO"


# =============================================================================
# 4. DESENHO
# =============================================================================
def misturar(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def texto(tela, fonte, s, cor, centro=None, esq=None, dire=None, dy=0):
    img = fonte.render(s, True, cor)
    r = img.get_rect()
    if centro:
        r.center = centro
    elif esq:
        r.midleft = esq
    elif dire:
        r.midright = dire
    r.y += dy
    tela.blit(img, r)
    return r


# -----------------------------------------------------------------------------
# ÍCONES (arquivos em assets/icons/)
# Cada ícone é um SVG (ou PNG) BRANCO com fundo transparente, desenhado no Figma
# em 256x256. O jogo pinta o ícone com a cor do tema na hora de desenhar e guarda o
# resultado em cache, então trocar de paleta recolore tudo sozinho.
# Detalhes "furados" (brilho da bomba, furo da engrenagem, "i" etc.) devem ser
# recortes transparentes no Figma, não cores de fundo.
# Para adicionar um ícone novo: salve assets/icons/<nome>.svg e chame
# desenhar_icone(tela, app, "<nome>", centro, tamanho, cor).
# -----------------------------------------------------------------------------
def carregar_icone(nome, tam):
    """Carrega assets/icons/<nome>.svg (ou .png) e redimensiona para tam x tam."""
    for ext in (".svg", ".png"):
        arq = PASTA_ICONES / (nome + ext)
        if arq.exists():
            img = pygame.image.load(str(arq)).convert_alpha()
            return pygame.transform.smoothscale(img, (tam, tam))
    raise FileNotFoundError(f"Ícone não encontrado: {PASTA_ICONES / nome}.svg")


def icone(app, nome, tam, cor, espelhar=False):
    """Devolve o ícone na cor pedida (cache por nome, tamanho, cor e espelhamento)."""
    tam = max(1, int(tam))
    chave = (nome, tam, tuple(cor), espelhar)
    cache = app["cache_icones"]
    if chave not in cache:
        img = carregar_icone(nome, tam)
        if espelhar:
            img = pygame.transform.flip(img, True, False)
        img.fill((*cor, 255), special_flags=pygame.BLEND_RGBA_MULT)   # pinta mantendo o alfa
        cache[chave] = img
    return cache[chave]


def desenhar_icone(tela, app, nome, centro, tam, cor, espelhar=False):
    img = icone(app, nome, tam, cor, espelhar)
    tela.blit(img, img.get_rect(center=(int(centro[0]), int(centro[1]))))


def desenhar_botao(tela, app, chave, rect, rotulo, fonte, ativo=False):
    t = app["tema"]
    passa = rect.collidepoint(app["mouse"])
    if ativo:
        pygame.draw.rect(tela, t["celula"], rect, border_radius=rect.height // 2)
        cor_txt = t["texto_cel"]
    else:
        if passa:
            pygame.draw.rect(tela, misturar(t["fundo"], t["texto"], 0.07), rect, border_radius=rect.height // 2)
        pygame.draw.rect(tela, t["linha"], rect, 2, border_radius=rect.height // 2)
        cor_txt = t["texto"]
    texto(tela, fonte, rotulo, cor_txt, centro=rect.center, dy=-4)
    app["ui"][chave] = rect


def fonte_numeros(app, tam):
    tamanho = max(14, int(tam * 0.72))
    if tamanho not in app["cache_fontes"]:
        app["cache_fontes"][tamanho] = pygame.font.SysFont(app["familia"], tamanho)
    return app["cache_fontes"][tamanho]


# ---- Paleta de temas (aparece no menu e no jogo) ----------------------------
def desenhar_paleta(tela, app):
    t, ui = app["tema"], app["ui"]
    centro = (LARGURA - 40, 76)
    if app["paleta_aberta"]:
        barra = pygame.Rect(12, 48, LARGURA - 24, 56)
        pygame.draw.rect(tela, t["fundo"], barra, border_radius=28)
        pygame.draw.rect(tela, t["linha"], barra, 2, border_radius=28)
        nomes = list(TEMAS)
        passo = (barra.width - 70) / len(nomes)
        for i, nome in enumerate(nomes):
            cx, cy = int(barra.x + 36 + passo * i), barra.centery
            tm = TEMAS[nome]
            pygame.draw.circle(tela, tm["fundo"], (cx, cy), 20)
            pygame.draw.circle(tela, tm["celula"], (cx, cy), 12)
            if nome == app["tema_nome"]:
                pygame.draw.circle(tela, t["celula"], (cx, cy), 24, 3)
            ui["tema_" + nome] = pygame.Rect(cx - 24, cy - 24, 48, 48)
        pygame.draw.circle(tela, t["celula"], centro, 28)
        desenhar_icone(tela, app, "paleta", centro, 48, t["texto_cel"])
    else:
        desenhar_icone(tela, app, "paleta", centro, 40, t["texto"])
    ui["paleta"] = pygame.Rect(centro[0] - 30, centro[1] - 30, 60, 60)


# ---- Tabuleiro ---------------------------------------------------------------
def oculta_em(jogo, l, c):
    return 0 <= l < jogo["linhas"] and 0 <= c < jogo["cols"] and jogo["estado"][l][c] != REVELADA


def revelada_em(jogo, l, c):
    return 0 <= l < jogo["linhas"] and 0 <= c < jogo["cols"] and jogo["estado"][l][c] == REVELADA


def desenhar_cantos_internos(tela, t, jogo, x0, y0, tam, r):
    """
    Arredonda os cantos INTERNOS (côncavos) do bloco de células ocultas.
    Um canto côncavo existe quando duas células ocultas vizinhas (vertical e horizontal)
    cercam uma célula revelada na diagonal. Nesse caso o "quina viva" da célula revelada
    é preenchida com um pequeno quadrado da cor das células e recortada por um círculo
    de raio r (o mesmo raio dos cantos externos), formando o arredondamento.
    """
    for l in range(jogo["linhas"]):
        for c in range(jogo["cols"]):
            if not oculta_em(jogo, l, c):
                continue
            for dl in (-1, 1):
                for dc in (-1, 1):
                    if not (oculta_em(jogo, l + dl, c) and oculta_em(jogo, l, c + dc)
                            and revelada_em(jogo, l + dl, c + dc)):
                        continue
                    # Ponto do canto compartilhado entre as 4 células
                    px = x0 + (c + (1 if dc > 0 else 0)) * tam
                    py = y0 + (l + (1 if dl > 0 else 0)) * tam
                    # Quadrado r x r dentro da célula revelada diagonal, encostado no canto
                    quad = pygame.Rect(px if dc > 0 else px - r, py if dl > 0 else py - r, r, r)
                    pygame.draw.rect(tela, t["celula"], quad)
                    tela.set_clip(quad)
                    pygame.draw.circle(tela, t["fundo"], (px + dc * r, py + dl * r), r)
                    tela.set_clip(None)


def desenhar_tabuleiro(tela, app, jogo, t_agora):
    t = app["tema"]
    x0, y0, tam = jogo["geo"]
    r = int(tam * 0.22)
    fonte = fonte_numeros(app, tam)

    for l in range(jogo["linhas"]):
        for c in range(jogo["cols"]):
            x, y = x0 + c * tam, y0 + l * tam
            rect = pygame.Rect(x, y, tam, tam)
            if jogo["estado"][l][c] == REVELADA:
                m, cor = int(tam * 0.12), t["linha"]
                pygame.draw.line(tela, cor, (x + m, y + 2), (x + tam - m, y + 2), 2)
                pygame.draw.line(tela, cor, (x + m, y + tam - 2), (x + tam - m, y + tam - 2), 2)
                pygame.draw.line(tela, cor, (x + 2, y + m), (x + 2, y + tam - m), 2)
                pygame.draw.line(tela, cor, (x + tam - 2, y + m), (x + tam - 2, y + tam - m), 2)
                n = jogo["vizinhas"][l][c]
                if n:
                    texto(tela, fonte, str(n), t["texto"], centro=rect.center)
                continue

            # Célula oculta: cantos arredondados só nas bordas externas do "bloco"
            cima, baixo = oculta_em(jogo, l - 1, c), oculta_em(jogo, l + 1, c)
            esq, dire = oculta_em(jogo, l, c - 1), oculta_em(jogo, l, c + 1)
            pygame.draw.rect(tela, t["celula"], rect,
                             border_top_left_radius=0 if (cima or esq) else r,
                             border_top_right_radius=0 if (cima or dire) else r,
                             border_bottom_left_radius=0 if (baixo or esq) else r,
                             border_bottom_right_radius=0 if (baixo or dire) else r)

            pos = (l, c)
            if pos in jogo["estouradas"]:
                if pos == jogo["bomba_fatal"]:
                    pygame.draw.rect(tela, t["perigo"], rect.inflate(-6, -6), border_radius=r)
                desenhar_icone(tela, app, "bomba", rect.center, tam * 0.81, t["texto_cel"])
            elif jogo["estado"][l][c] == MARCADA:
                desenhar_icone(tela, app, "bandeira", rect.center, tam, t["texto_cel"])

    # Cantos internos arredondados (côncavos), iguais aos externos
    desenhar_cantos_internos(tela, t, jogo, x0, y0, tam, r)

    # Anéis de explosão: desenhados DEPOIS de todas as células, para nunca ficarem
    # cobertos pelos quadrados vizinhos (o efeito aparece inteiro por cima do tabuleiro).
    for (l, c), t0 in jogo["estouradas"].items():
        idade = t_agora - t0
        if 0 <= idade < 0.55:
            raio = int(tam * (0.4 + idade * 1.8))
            anel = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
            alfa = int(230 * (1 - idade / 0.55))
            # Anel em duas camadas: a borda larga (texto_cel) contrasta com as células ocultas
            # e o traço central (texto) contrasta com o fundo; assim o efeito aparece em
            # qualquer tema, inclusive quando "texto" e "celula" são cores parecidas.
            pygame.draw.circle(anel, (*t["texto_cel"], alfa), (raio + 4, raio + 4), raio, 6)
            pygame.draw.circle(anel, (*t["texto"], alfa), (raio + 4, raio + 4), raio, 2)
            centro = (x0 + c * tam + tam // 2, y0 + l * tam + tam // 2)
            tela.blit(anel, anel.get_rect(center=centro))


def pos_para_celula(jogo, pos):
    x0, y0, tam = jogo["geo"]
    c, l = (pos[0] - x0) // tam, (pos[1] - y0) // tam
    if 0 <= l < jogo["linhas"] and 0 <= c < jogo["cols"] and pos[0] >= x0 and pos[1] >= y0:
        return int(l), int(c)
    return None


# ---- HUD ---------------------------------------------------------------------
def desenhar_hud(tela, app, jogo):
    t, F = app["tema"], app["fontes"]
    desenhar_icone(tela, app, "voltar", (40, 76), 40, t["texto"])
    app["ui"]["voltar"] = pygame.Rect(5, 40, 70, 70)
    cx = LARGURA // 2
    desenhar_icone(tela, app, "bomba", (cx - 24, 62), 30, t["texto"])
    texto(tela, F["m"], str(bombas_restantes(jogo)), t["texto"], esq=(cx - 6, 62), dy=-3)
    if jogo["fase"] != "AGUARDANDO":
        sub = misturar(t["fundo"], t["texto"], 0.7)
        texto(tela, F["p"], formatar_tempo(tempo_decorrido(jogo)), sub, centro=(cx, 92))


def desenhar_seletor_modo(tela, app, jogo):
    """Botão de alternância Revelar / Marcar (alternativa ao clique direito, ideal p/ toque)."""
    t, ui = app["tema"], app["ui"]
    pill = pygame.Rect(0, 0, 190, 62)
    pill.center = (LARGURA // 2, ALTURA - 70)
    pygame.draw.rect(tela, t["fundo"], pill, border_radius=31)
    pygame.draw.rect(tela, t["linha"], pill, 2, border_radius=31)
    metades = {"modo_revelar": (pill.x + 48, False), "modo_bandeira": (pill.right - 48, True)}
    for chave, (cx, eh_bandeira) in metades.items():
        ativo = jogo["modo_bandeira"] == eh_bandeira
        if ativo:
            pygame.draw.circle(tela, t["celula"], (cx, pill.centery), 25)
        cor = t["texto_cel"] if ativo else t["texto"]
        desenhar_icone(tela, app, "bandeira" if eh_bandeira else "engrenagem",
                       (cx, pill.centery), 38 if eh_bandeira else 30, cor)
        ui[chave] = pygame.Rect(cx - 30, pill.y, 60, pill.height)


# ---- Pop-up de resultado -----------------------------------------------------
def desenhar_popup(tela, app, jogo):
    t, F = app["tema"], app["fontes"]
    res = jogo["resultado"]
    veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    veu.fill((*t["fundo"], 175))
    tela.blit(veu, (0, 0))

    painel = pygame.Rect(40, 170, LARGURA - 80, 460)
    pygame.draw.rect(tela, misturar(t["fundo"], t["texto"], 0.07), painel, border_radius=26)
    pygame.draw.rect(tela, t["linha"], painel, 2, border_radius=26)
    cx = painel.centerx

    titulo = "Vitória!" if res["vitoria"] else "Fim de jogo"
    texto(tela, F["g"], titulo, t["celula"], centro=(cx, painel.y + 45))
    texto(tela, F["mini"], f"Dificuldade {jogo['dif']}", misturar(t["fundo"], t["texto"], 0.6),
          centro=(cx, painel.y + 78))
    texto(tela, F["xl"], str(res["pontos"]), t["texto"], centro=(cx, painel.y + 130))
    texto(tela, F["mini"], "pontos", misturar(t["fundo"], t["texto"], 0.6), centro=(cx, painel.y + 168))
    texto(tela, F["p"], f"Tempo {formatar_tempo(res['tempo'])}   ·   Cliques {res['cliques']}",
          t["texto"], centro=(cx, painel.y + 202))

    # Comparativo com high-scores
    if res["vitoria"] and res["posicao"] == 1:
        texto(tela, F["p"], "Novo recorde!", t["celula"], centro=(cx, painel.y + 236))
    else:
        texto(tela, F["p"], f"Melhor: {max(res['melhor_antes'], 0)} pts", t["texto"],
              centro=(cx, painel.y + 236))
    top = app["recordes"].get(jogo["dif"], [])[:3]
    for i in range(3):
        y = painel.y + 272 + i * 26
        if i < len(top):
            destaque = res["vitoria"] and res["posicao"] == i + 1
            cor = t["celula"] if destaque else misturar(t["fundo"], t["texto"], 0.75)
            texto(tela, F["p"], f"{i + 1}.  {top[i]['pontos']} pts   {formatar_tempo(top[i]['tempo'])}",
                  cor, centro=(cx, y))
        else:
            texto(tela, F["p"], f"{i + 1}.  —", misturar(t["fundo"], t["texto"], 0.4), centro=(cx, y))

    desenhar_botao(tela, app, "novamente", pygame.Rect(painel.x + 30, painel.bottom - 108, painel.width - 60, 44),
                   "Jogar de novo", F["p"], ativo=True)
    desenhar_botao(tela, app, "menu", pygame.Rect(painel.x + 30, painel.bottom - 56, painel.width - 60, 40),
                   "Menu", F["p"])


def desenhar_confetes(tela, jogo):
    for p in jogo["confetes"]:
        ca, sa = math.cos(p["ang"]), math.sin(p["ang"])
        hw, hh = p["w"] / 2, p["h"] / 2
        pts = [(p["x"] + dx * ca - dy * sa, p["y"] + dx * sa + dy * ca)
               for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
        pygame.draw.polygon(tela, p["cor"], pts)


# ---- Telas -------------------------------------------------------------------
def desenhar_jogo(tela, app, t_agora):
    jogo = app["jogo"]
    duracao_transicao = 0.35  # Tempo em segundos
    t_decorrido = t_agora - jogo.get("t_inicio_transicao", t_agora)

    if t_decorrido < duracao_transicao:
        # Progresso normalizado (0.0 a 1.0) com easing out-quad para suavidade
        progresso = min(1.0, t_decorrido / duracao_transicao)
        p_suave = 1.0 - (1.0 - progresso) ** 2

        # Escala: inicia em 60% (0.6) e vai até 100% (1.0)
        escala = 0.6 + 0.4 * p_suave
        
        # Opacidade: inicia em 60% (153/255) e vai até 100% (255)
        opacidade = int(255 * (0.6 + 0.4 * p_suave))

        # Renderiza a cena do jogo em uma superfície temporária
        surf_temp = pygame.Surface((LARGURA, ALTURA))
        surf_temp.fill(app["tema"]["fundo"])
        _desenhar_conteudo_jogo(surf_temp, app, t_agora)

        # Redimensiona a superfície com interpolação suave
        larg_nova = max(1, int(LARGURA * escala))
        alt_nova = max(1, int(ALTURA * escala))
        surf_redim = pygame.transform.smoothscale(surf_temp, (larg_nova, alt_nova))
        surf_redim.set_alpha(opacidade)

        # Desenha a cena centralizada na janela
        rect = surf_redim.get_rect(center=(LARGURA // 2, ALTURA // 2))
        tela.blit(surf_redim, rect)
    else:
        # Renderização normal sem custo adicional de superfície após o término da transição
        _desenhar_conteudo_jogo(tela, app, t_agora)

def _desenhar_conteudo_jogo(tela, app, t_agora):
    """Renderiza os elementos nativos da tela do jogo."""
    jogo = app["jogo"]
    desenhar_hud(tela, app, jogo)
    desenhar_tabuleiro(tela, app, jogo, t_agora)
    if jogo["fase"] in ("AGUARDANDO", "JOGANDO"):
        desenhar_seletor_modo(tela, app, jogo)
    if jogo["fase"] == "AGUARDANDO":
        texto(tela, app["fontes"]["mini"], "toque numa célula para começar",
                misturar(app["tema"]["fundo"], app["tema"]["texto"], 0.6), centro=(LARGURA // 2, 116))
    desenhar_confetes(tela, jogo)
    if jogo["fase"] == "RESULTADO":
        desenhar_popup(tela, app, jogo)

def desenhar_menu(tela, app):
    t, F, cfg = app["tema"], app["fontes"], app["config"]
    cx = LARGURA // 2
    # Logo
    desenhar_icone(tela, app, "bomba", (cx, 200), 235, t["celula"])
    # Seletor de dificuldade
    y_sel = 416
    nome = ORDEM_DIF[cfg["dif_idx"]]
    texto(tela, F["m"], nome, t["texto"], centro=(cx, y_sel), dy=-4)
    cor_seta = misturar(t["fundo"], t["texto"], 0.75)
    desenhar_icone(tela, app, "seta", (92, y_sel), 36, cor_seta, espelhar=True)
    desenhar_icone(tela, app, "seta", (LARGURA - 92, y_sel), 36, cor_seta)
    app["ui"]["dif_ant"] = pygame.Rect(50, y_sel - 30, 90, 60)
    app["ui"]["dif_prox"] = pygame.Rect(LARGURA - 140, y_sel - 30, 90, 60)
    # Novo jogo
    y_novo = y_sel + 60
    desenhar_botao(tela, app, "novo", pygame.Rect(58, y_novo - 22, LARGURA - 116, 44), "Novo Jogo", F["m"])

    # Ícones inferiores
    y_ic = ALTURA - 60
    desenhar_icone(tela, app, "lista", (cx - 60, y_ic), 90, t["texto"])
    desenhar_icone(tela, app, "info", (cx + 60, y_ic), 48, t["texto"])
    app["ui"]["recordes"] = pygame.Rect(cx - 100, y_ic - 30, 80, 60)
    app["ui"]["ajuda"] = pygame.Rect(cx + 20, y_ic - 30, 80, 60)


def desenhar_recordes(tela, app):
    t, F = app["tema"], app["fontes"]
    desenhar_icone(tela, app, "voltar", (40, 76), 40, t["texto"])
    app["ui"]["voltar"] = pygame.Rect(5, 40, 70, 70)
    texto(tela, F["g"], "Recordes", t["texto"], centro=(LARGURA // 2, 150))
    y = 215
    for dif in ORDEM_DIF:
        texto(tela, F["m"], dif, t["celula"], esq=(50, y))
        lista = app["recordes"].get(dif, [])
        for i in range(3):
            y += 30
            if i < len(lista):
                r = lista[i]
                texto(tela, F["p"], f"{i + 1}.  {r['pontos']} pts   {formatar_tempo(r['tempo'])}   {r['data']}",
                      t["texto"], esq=(60, y))
            else:
                texto(tela, F["p"], f"{i + 1}.  —", misturar(t["fundo"], t["texto"], 0.4), esq=(60, y))
        y += 50


def desenhar_ajuda(tela, app):
    t, F = app["tema"], app["fontes"]
    desenhar_icone(tela, app, "voltar", (40, 76), 40, t["texto"])
    app["ui"]["voltar"] = pygame.Rect(5, 40, 70, 70)
    texto(tela, F["g"], "Como jogar", t["texto"], centro=(LARGURA // 2, 150))
    linhas = [
        "Revele todas as células sem bombas.",
        "Os números indicam quantas bombas",
        "existem nas 8 células adjacentes.",
        "",
        "Clique esquerdo: revelar",
        "Clique direito / tecla F: marcar",
        "R: nova partida    ESC: voltar",
        "",
        "O contador mostra bombas restantes.",
        "O primeiro clique nunca é uma bomba.",
        "",
        
    ]
    for i, s in enumerate(linhas):
        texto(tela, F["p"], s, t["texto"], centro=(LARGURA // 2, 215 + i * 30))


def desenhar_interface(tela, app, t_agora):
    """Redesenha a tela inteira; também reconstrói o mapa de botões clicáveis (app['ui'])."""
    app["ui"] = {}
    app["mouse"] = pygame.mouse.get_pos()
    tela.fill(app["tema"]["fundo"])
    match app["tela"]:
        case "MENU":
            desenhar_menu(tela, app)
        case "JOGO":
            desenhar_jogo(tela, app, t_agora)
        case "RECORDES":
            desenhar_recordes(tela, app)
        case "AJUDA":
            desenhar_ajuda(tela, app)
    if app["tela"] == "MENU":        # a paleta só existe no menu inicial
        desenhar_paleta(tela, app)


# =============================================================================
# 5. EVENTOS, FLUXO (match-case) E LOOP PRINCIPAL
# =============================================================================
def iniciar_jogo(app):
    cfg = app["config"]
    app["jogo"] = criar_estado_jogo(ORDEM_DIF[cfg["dif_idx"]])
    app["jogo"]["t_inicio_transicao"] = agora()  # Marca o tempo inicial da animação
    app["paleta_aberta"] = False
    app["tela"] = "JOGO"


def voltar_menu(app):
    app["paleta_aberta"] = False
    app["tela"] = "MENU"


def mudar_dificuldade(app, passo):
    cfg = app["config"]
    cfg["dif_idx"] = (cfg["dif_idx"] + passo) % len(ORDEM_DIF)


def definir_tema(app, nome):
    app["tema_nome"], app["tema"] = nome, TEMAS[nome]


def acionar_botao(app, chave):
    """Roteador central dos botões da interface (fluxo de menus com match-case)."""
    jogo = app.get("jogo")
    match chave:
        case "paleta":
            app["paleta_aberta"] = not app["paleta_aberta"]
        case "voltar":
            voltar_menu(app)
        case "dif_ant":
            mudar_dificuldade(app, -1)
        case "dif_prox":
            mudar_dificuldade(app, +1)
        case "novo" | "novamente":
            iniciar_jogo(app)
        case "menu":
            voltar_menu(app)
        case "recordes":
            app["paleta_aberta"] = False
            app["tela"] = "RECORDES"
        case "ajuda":
            app["paleta_aberta"] = False
            app["tela"] = "AJUDA"
        case "modo_revelar" if jogo:
            jogo["modo_bandeira"] = False
        case "modo_bandeira" if jogo:
            jogo["modo_bandeira"] = True
        case _ if chave.startswith("tema_"):
            definir_tema(app, chave[len("tema_"):])
            app["paleta_aberta"] = False


def tratar_clique(app, pos, botao):
    if app["tela"] == "JOGO" and app.get("jogo"):
        if agora() - app["jogo"].get("t_inicio_transicao", 0) < 0.35:
            return
    # 1) Botões da interface (de cima para baixo: o último desenhado vence)
    if botao == 1:
        for chave, rect in reversed(list(app["ui"].items())):
            if rect.collidepoint(pos):
                acionar_botao(app, chave)
                return
    # 2) Tabuleiro
    if app["tela"] == "JOGO" and app["jogo"]["fase"] in ("AGUARDANDO", "JOGANDO"):
        jogo = app["jogo"]
        alvo = pos_para_celula(jogo, pos)
        if alvo:
            match botao:
                case 1:
                    processar_clique(jogo, *alvo)
                case 3:
                    marcar_celula(jogo, *alvo)


def tratar_teclado(app, tecla):
    match tecla:
        case pygame.K_ESCAPE:
            if app["paleta_aberta"]:
                app["paleta_aberta"] = False
            elif app["tela"] != "MENU":
                voltar_menu(app)
        case pygame.K_r if app["tela"] == "JOGO":
            iniciar_jogo(app)
        case pygame.K_f if app["tela"] == "JOGO" and app["jogo"]["fase"] in ("AGUARDANDO", "JOGANDO"):
            app["jogo"]["modo_bandeira"] = not app["jogo"]["modo_bandeira"]


def tratar_eventos(app):
    for ev in pygame.event.get():
        match ev.type:
            case pygame.QUIT:
                app["rodando"] = False
            case pygame.MOUSEBUTTONDOWN:
                tratar_clique(app, ev.pos, ev.button)
            case pygame.KEYDOWN:
                tratar_teclado(app, ev.key)


def atualizar_jogo(app, dt, t):
    jogo = app["jogo"]
    match jogo["fase"]:
        case "ANIM_DERROTA":
            animar_derrota(app, jogo, t)
        case "ANIM_VITORIA":
            animar_vitoria(app, jogo, t, dt)
        case "RESULTADO":
            atualizar_confetes(jogo, dt)


def criar_app():
    familia = "segoeui,helveticaneue,ubuntu,dejavusans,arial"
    mk = lambda tam: pygame.font.SysFont(familia, tam)
    return {
        "rodando": True, "tela": "MENU", "jogo": None,
        "tema_nome": TEMA_PADRAO, "tema": TEMAS[TEMA_PADRAO],
        "paleta_aberta": False,
        "config": {"dif_idx": 0},
        "recordes": carregar_recordes(),
        "ui": {}, "mouse": (0, 0),
        "familia": familia, "cache_fontes": {}, "cache_icones": {},
        "fontes": {"mini": mk(15), "p": mk(20), "m": mk(28), "g": mk(38), "xl": mk(64)},
    }


def main():
    pygame.init()
    pygame.display.set_caption("Campo Minado")
    tela = pygame.display.set_mode((LARGURA, ALTURA), pygame.SCALED | pygame.RESIZABLE)
    relogio = pygame.time.Clock()
    app = criar_app()
    while app["rodando"]:
        dt = relogio.tick(FPS) / 1000
        t = agora()
        tratar_eventos(app)
        if app["tela"] == "JOGO":
            atualizar_jogo(app, dt, t)
        desenhar_interface(tela, app, t)
        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()
