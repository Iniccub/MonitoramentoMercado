import streamlit as st
import requests
from serpapi import GoogleSearch
from bs4 import BeautifulSoup
import concurrent.futures  # Para processamento paralelo
import time
from typing import List, Dict  # Para tipagem
import os
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import base64
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Carrega as variáveis de ambiente
load_dotenv()

# Configurações iniciais
st.set_page_config(
    page_title="Monitoramento de Mercado",
    page_icon="icon.png",
    layout="wide",
    initial_sidebar_state="collapsed"  # Melhora o espaço útil inicial
)

# Cache para resultados de busca
@st.cache_data(ttl=3600)  # Cache por 1 hora
def buscar_noticias(tema: str, serpapi_key: str) -> List[str]:
    params = {
        'q': tema,
        'tbm': 'nws',
        'hl': 'pt-br',
        'gl': 'br',
        'api_key': serpapi_key
    }
    try:
        search = GoogleSearch(params)
        resultados = search.get_dict()
        return [noticia.get('link') for noticia in resultados.get('news_results', []) if noticia.get('link')]
    except Exception as e:
        st.error(f"Erro na busca de notícias: {str(e)}")
        return []

# Função otimizada para extrair texto de uma URL
def limpar_texto(texto: str) -> str:
    """Remove caracteres especiais e formata o texto."""
    import re
    texto = re.sub(r'\s+', ' ', texto)  # Remove espaços múltiplos
    texto = re.sub(r'[^\w\s.,!?-]', '', texto)  # Remove caracteres especiais
    return texto.strip()

def extrair_texto_url(url: str, headers: Dict[str, str]) -> dict:
    try:
        with requests.get(url, headers=headers, timeout=10) as response:
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove elementos irrelevantes
            for elemento in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
                elemento.decompose()
            
            # Extrai texto de elementos relevantes, incluindo tabelas
            textos = []
            
            # Processa elementos de texto normais
            for p in soup.find_all(['p', 'article', 'section', 'h1', 'h2', 'h3']):
                if len(p.get_text().strip()) > 50:
                    textos.append(p.get_text())
            
            # Processa tabelas
            for tabela in soup.find_all('table'):
                texto_tabela = []
                # Processa cabeçalho da tabela
                headers = []
                for th in tabela.find_all('th'):
                    headers.append(th.get_text().strip())
                if headers:
                    texto_tabela.append(" | ".join(headers))
                    texto_tabela.append("-" * 50)  # Linha separadora
                
                # Processa linhas da tabela
                for tr in tabela.find_all('tr'):
                    linha = []
                    for td in tr.find_all('td'):
                        linha.append(td.get_text().strip())
                    if linha:
                        texto_tabela.append(" | ".join(linha))
                
                if texto_tabela:
                    textos.append("\n".join(texto_tabela))
            
            # Extrai imagens relevantes
            imagens = []
            for img in soup.find_all('img'):
                src = img.get('src')
                alt = img.get('alt', '')
                if src and (src.startswith('http') or src.startswith('/')):
                    # Normaliza URLs relativas
                    if src.startswith('/'):
                        base_url = '/'.join(url.split('/')[:3])  # http(s)://dominio.com
                        src = base_url + src
                    imagens.append({'url': src, 'alt': alt})
            
            texto_final = '\n\n'.join(textos)
            return {
                'texto': limpar_texto(texto_final),
                'imagens': imagens[:5]  # Limita a 5 imagens por notícia
            }
    except Exception as e:
        st.error(f"Erro ao extrair texto: {str(e)}")
        return {'texto': '', 'imagens': []}

# Inicializar a sessão de estado para armazenar o histórico da conversa
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Definir variáveis globais
try:
    api_key_OpenaAI = st.secrets["openai"]["api_key"]
    serpapi_key = st.secrets["serpapi"]["api_key"]
except Exception as e:
    st.error('Chaves de API não encontradas nas configurações do Streamlit')
    st.stop()

# Validação adicional da chave OpenAI
if not api_key_OpenaAI.startswith('sk-'):
    st.error('Formato da chave da API OpenAI inválido')
    st.stop()

api_url = 'https://api.openai.com/v1/chat/completions'
headers_api = {
    'Authorization': f'Bearer {api_key_OpenaAI.strip()}',
    'Content-Type': 'application/json'
}

# Criação de colunas para o logotipo e título
col1, col2, col3 = st.columns([0.6, 5, 0.6])

with col1:
    st.image("icon.png", width=100)

with col2:
    # Cabeçalho
    with st.container():
        # Exiba o título e o subtítulo centralizados
        st.markdown(
            "<h1 style='text-align: center; font-family: Open Sauce; color: #4D268C;'>"
            "Monitoramento de Mercado - Rede Lius</h1>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<h3 style='text-align: center;font-family: Open Sauce; color: #FCA629;'>"
            "Ferramenta de Monitoramento de Mercado e análise de cenários econômicos da Rede Lius Agostinianos</h3>",
            unsafe_allow_html=True
        )

    st.write("---")

    # Define as opções do menu suspenso
    opcoes = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-nano"]

    # Cria o menu suspenso com as opções
    modelo = st.selectbox("Selecione um modelo de IA para fazer a análise:", opcoes)

    # Exibe a opção selecionada
    st.write("Você usará o modelo (🤖 {}) para fazer a análise".format(modelo))

    st.write("__")

    # Textos de descrição dos modelos de IA
    texto_GPT4o_mini = "🤖 - O GPT 4o-mini é o mais recente modelo compacto da série O. Ele é otimizado para raciocínio rápido e eficaz, com desempenho excepcionalmente eficiente em tarefas visuais e de codificação. A pesquisa é a de menor custo de todos os modelos."
    texto_GPT4o = "🤖 - O GPT-4o (\"o\" de \"omni\") é o modelo topo de linha, versátil e altamente inteligente. Ele aceita entradas de texto e imagem e produz saídas de texto (incluindo Saídas Estruturadas). É o melhor modelo para a maioria das tarefas e mais capaz dos modelos da série O. A pesquisa tem maior custo, porém mais baixo em comparação aos modelos mais complexos."
    texto_GPT41_nano = "🤖 - O GPT-4.1 nano é o modelo GPT-4.1 mais rápido e econômico."

    # Deploy dos textos de descrição dos modelos de IA
    st.markdown(f"<div style='text-align: justify; line-height: 1.6;'>{texto_GPT4o_mini}</div>", unsafe_allow_html=True)
    st.write("")
    st.markdown(f"<div style='text-align: justify; line-height: 1.6;'>{texto_GPT4o}</div>", unsafe_allow_html=True)
    st.write("")
    st.markdown(f"<div style='text-align: justify; line-height: 1.6;'>{texto_GPT41_nano}</div>", unsafe_allow_html=True)

    st.write("---")

    # Entrada de dados de pesquisa no Google
    tema = st.text_input(
        "Digite o termo que você deseja pesquisar no Google Notícias:",
        placeholder="Digite aqui sua pesquisa",
        label_visibility="visible"
    )
    # Entrada de texto da diretriz da IA
    diretriz = st.text_input(
        "Qual a diretriz de análise da IA?",
        placeholder="Digite aqui a diretriz com a qual você quer que a IA trabalhe",
        label_visibility="visible"
    )

    # Botão para iniciar a análise
    # Modificação no bloco de processamento de links
    # No bloco onde você usa a serpapi_key (remover a linha que busca do os.getenv)
    if st.button("Analisar"):
        if tema and diretriz:
            with st.spinner('Buscando e processando notícias...'):
                links = buscar_noticias(tema, serpapi_key)
                
                if links:
                    # Processamento paralelo das URLs
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
                    }
                    
                    # Processamento paralelo otimizado
                    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                        futures = [executor.submit(extrair_texto_url, link, headers) for link in links]
                        textos = []
                        
                        # Barra de progresso
                        progress_bar = st.progress(0)
                        for i, future in enumerate(concurrent.futures.as_completed(futures)):
                            resultado = future.result()
                            if resultado and resultado['texto']:  # Verifica se há texto no resultado
                                textos.append(resultado['texto'])
                            progress_bar.progress((i + 1) / len(futures))
                        
                        texto_completo = '\n\n'.join(textos)
                        
                        # Otimização do prompt para a IA
                        prompt_otimizado = f"""
                        Analise o seguinte conjunto de notícias sobre '{tema}' e responda de acordo com a diretriz: '{diretriz}'
                        
                        Pontos importantes a considerar:
                        1. Foque nos fatos mais relevantes e atuais
                        2. Identifique tendências e padrões
                        3. Considere o impacto no contexto específico da Rede Lius
                        4. Forneça insights acionáveis
                        
                        Texto para análise: {texto_completo[:8000]}
                        """
                        
                        # Atualiza as mensagens com o prompt otimizado
                        st.session_state.messages.append({
                            'role': 'user',
                            'content': prompt_otimizado,
                            'exibir': False
                        })

                        # Configuração otimizada para a API da OpenAI
                        body_message = {
                            'model': modelo,
                            'messages': st.session_state.messages,
                            'temperature': 0.3,  # Reduzido para maior precisão
                            'max_tokens': 4000,
                            'presence_penalty': 0.1,  # Encoraja diversidade moderada
                            'frequency_penalty': 0.1  # Evita repetições
                        }

                    try:
                        response_api = requests.post(api_url, headers=headers_api, json=body_message)
                        response_api.raise_for_status()
                        resposta = response_api.json()['choices'][0]['message']['content']
                        st.session_state.messages.append({'role': 'assistant', 'content': resposta})
                    except Exception as e:
                        st.error(f"Erro ao chamar a API da OpenAI: {e}")


    # Mostrar o histórico da conversa
    for msg in st.session_state.messages:
        if msg.get('exibir', True): # Exibe apensa se exibir for True ou não estiver definido
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])

    # Substituir o chat_input por um text_input regular
    nova_pergunta = st.text_input(
        "Deseja continuar a análise com outra pergunta?",
        key="nova_pergunta_input"
    )

    # Adicionar um botão para enviar a pergunta
    if st.button("Enviar pergunta", key="enviar_pergunta"):
        if nova_pergunta:
            st.session_state.messages.append({'role': 'user', 'content': nova_pergunta})

            body_message = {
                'model': modelo,
                'messages': st.session_state.messages,
                'temperature': 0.2,
                'max_tokens': 4000
            }

            try:
                response_api = requests.post(api_url, headers=headers_api, json=body_message)
                response_api.raise_for_status()
                nova_resposta = response_api.json()['choices'][0]['message']['content']
                st.session_state.messages.append({'role': 'assistant', 'content': nova_resposta})
                with st.chat_message("assistant"):
                    st.markdown(nova_resposta)
            except Exception as e:
                st.error(f"Erro ao continuar a conversa com a API: {e}")

# Rodapé com copyright
st.markdown("""
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f0f0f0;
        color: #333;
        text-align: center;
        padding: 10px;
        font-size: 14px;
    }
    </style>
    <div class="footer">
        © 2025 FP&A e Orçamento - Rede Lius. Todos os direitos reservados.
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.image("CSA.png", width=100)


def pre_processar_texto_ia(texto):
    """
    Pré-processa o texto da IA para melhorar a formatação.
    
    Args:
        texto: Texto original da IA
        
    Returns:
        str: Texto pré-processado
    """
    import re
    
    # Substituir múltiplos asteriscos por formatação adequada
    texto_processado = texto
    
    # Substituir padrões de negrito e itálico
    # Primeiro, substituir padrões de negrito e itálico combinados
    texto_processado = re.sub(r'\*\*\*(.*?)\*\*\*', r'<b><i>\1</i></b>', texto_processado)
    
    # Depois, substituir padrões de negrito
    texto_processado = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto_processado)
    
    # Por último, substituir padrões de itálico
    texto_processado = re.sub(r'\*(.*?)\*', r'<i>\1</i>', texto_processado)
    
    # Substituir caracteres de marcação por HTML
    texto_processado = texto_processado.replace('---', '<hr/>')
    texto_processado = re.sub(r'==(.*?)==', r'<u>\1</u>', texto_processado)
    
    # Melhorar formatação de listas
    linhas = texto_processado.split('\n')
    for i in range(len(linhas)):
        # Converter listas numeradas
        if re.match(r'^\d+\.\s', linhas[i].strip()):
            numero = linhas[i].strip().split('.')[0]
            resto = '.'.join(linhas[i].strip().split('.')[1:])
            linhas[i] = f"{numero}. {resto.strip()}"
    
    return '\n'.join(linhas)

def destacar_numeros_no_texto(texto):
    """
    Destaca números no texto para melhor visualização.
    
    Args:
        texto: Texto contendo números
        
    Returns:
        str: Texto com números destacados
    """
    import re
    # Encontrar todos os números no texto
    numeros = re.findall(r'\d+[.,]?\d*%?', texto)
    
    # Substituir cada número por uma versão destacada
    texto_formatado = texto
    for numero in numeros:
        texto_formatado = texto_formatado.replace(numero, f"<b><font color='#4D268C'>{numero}</font></b>")
    
    return texto_formatado

def formatar_texto_rico(texto):
    """
    Aplica formatação rica ao texto.
    
    Args:
        texto: Texto original
        
    Returns:
        str: Texto com formatação rica
    """
    import re
    
    # Substituir marcações de negrito e itálico
    texto_formatado = texto
    
    # Substituir padrões de negrito
    texto_formatado = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto_formatado)
    
    # Substituir padrões de itálico
    texto_formatado = re.sub(r'\*(.*?)\*', r'<i>\1</i>', texto_formatado)
    
    # Substituir marcações de sublinhado
    texto_formatado = re.sub(r'__(.*?)__', r'<u>\1</u>', texto_formatado)
    
    # Substituir marcações de tachado
    texto_formatado = re.sub(r'~~(.*?)~~', r'<strike>\1</strike>', texto_formatado)
    
    # Destacar palavras-chave comuns em análises de mercado
    palavras_chave = [
        'crescimento', 'aumento', 'redução', 'queda', 'tendência', 
        'mercado', 'economia', 'inflação', 'PIB', 'taxa', 
        'investimento', 'expansão', 'contração', 'recessão', 'recuperação',
        'oportunidade', 'desafio', 'risco', 'estratégia', 'competição',
        'inovação', 'tecnologia', 'sustentabilidade', 'regulação', 'consumidor'
    ]
    
    for palavra in palavras_chave:
        # Verificar se a palavra existe no texto (como palavra completa)
        if re.search(r'\b' + palavra + r'\b', texto_formatado, re.IGNORECASE):
            # Substituir apenas palavras completas, preservando maiúsculas/minúsculas
            texto_formatado = re.sub(
                r'\b(' + palavra + r')\b', 
                r'<font color="#4D268C">\1</font>', 
                texto_formatado, 
                flags=re.IGNORECASE
            )
    
    return texto_formatado

def gerar_relatorio_executivo(tema, diretriz, resposta_ia, links_utilizados=None):
    """
    Gera um relatório executivo em PDF com os resultados da análise de mercado.
    
    Args:
        tema: Tema pesquisado
        diretriz: Diretriz de análise
        resposta_ia: Resposta da IA
        links_utilizados: Lista de links utilizados na pesquisa
    
    Returns:
        bytes: Conteúdo do PDF em formato base64 para download
    """
    buffer = BytesIO()
    
    # Configuração do documento
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        leftMargin=72,
        rightMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para títulos e subtítulos
    styles.add(ParagraphStyle(
        name='TituloRelatorio',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=16,
        textColor=colors.HexColor('#4D268C'),  # Cor da Rede Lius
        alignment=1,  # Centralizado
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='SubtituloRelatorio',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#FCA629'),  # Cor secundária
        alignment=0,  # Alinhado à esquerda
        fontName='Helvetica-Bold',
        borderPadding=5,
        borderWidth=0,
        borderColor=colors.HexColor('#FCA629'),
        borderRadius=5
    ))
    
    styles.add(ParagraphStyle(
        name='TextoNormal',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        spaceAfter=10,
        alignment=4  # Justificado
    ))
    
    styles.add(ParagraphStyle(
        name='Destaque',
        parent=styles['Normal'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#4D268C'),
        backColor=colors.HexColor('#F5F5F5'),
        borderPadding=10,
        borderWidth=1,
        borderColor=colors.HexColor('#E0E0E0'),
        borderRadius=5,
        spaceAfter=15,
        alignment=4  # Justificado
    ))
    
    styles.add(ParagraphStyle(
        name='Rodape',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        alignment=1  # Centralizado
    ))
    
    # Adicionar estilos para formatação especial
    styles.add(ParagraphStyle(
        name='ItemLista',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        leftIndent=20,
        firstLineIndent=0,
        bulletIndent=10,
        spaceBefore=2,
        spaceAfter=2,
        alignment=0  # Alinhado à esquerda
    ))
    
    styles.add(ParagraphStyle(
        name='TituloSecao',
        parent=styles['Heading3'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#4D268C'),
        spaceBefore=12,
        spaceAfter=6,
        alignment=0  # Alinhado à esquerda
    ))
    
    styles.add(ParagraphStyle(
        name='Citacao',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        leftIndent=30,
        rightIndent=30,
        textColor=colors.HexColor('#555555'),
        italics=True,
        spaceBefore=6,
        spaceAfter=6,
        alignment=4  # Justificado
    ))
    
    # Conteúdo do relatório
    conteudo = []
    
    # Cabeçalho com logo e título
    cabecalho_dados = [
        [Image("icon.png", width=80, height=80), 
         Paragraph(f"<b>Relatório de Monitoramento de Mercado</b><br/><br/>Rede Lius Agostinianos", styles['TituloRelatorio'])]
    ]
    
    cabecalho_tabela = Table(cabecalho_dados, colWidths=[100, 350])
    cabecalho_tabela.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (1, 0), 'MIDDLE'),
    ]))
    
    conteudo.append(cabecalho_tabela)
    conteudo.append(Spacer(1, 20))
    
    # Data e informações do relatório
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    info_relatorio = [
        [Paragraph(f"<b>Data:</b> {data_atual}", styles['TextoNormal']), 
         Paragraph(f"<b>Tema:</b> {tema}", styles['TextoNormal'])]
    ]
    
    info_tabela = Table(info_relatorio, colWidths=[225, 225])
    info_tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#F8F8F8')),
        ('BOX', (0, 0), (1, 0), 1, colors.HexColor('#E0E0E0')),
        ('PADDING', (0, 0), (1, 0), 10),
    ]))
    
    conteudo.append(info_tabela)
    conteudo.append(Spacer(1, 25))
    
    # Ícones para cada seção (usando caracteres Unicode como substitutos)
    icone_sumario = "📊 "  # Ícone para sumário
    icone_escopo = "🔍 "   # Ícone para escopo
    icone_analise = "📈 "  # Ícone para análise
    icone_fontes = "📚 "   # Ícone para fontes
    icone_conclusao = "✅ " # Ícone para conclusão
    
    # Sumário Executivo
    conteudo.append(Paragraph(f"{icone_sumario}SUMÁRIO EXECUTIVO", styles['SubtituloRelatorio']))
    
    # Extrair primeiro parágrafo da resposta para o sumário
    primeiro_paragrafo = resposta_ia.split('\n\n')[0] if '\n\n' in resposta_ia else resposta_ia
    conteudo.append(Paragraph(primeiro_paragrafo, styles['Destaque']))
    conteudo.append(Spacer(1, 20))
    
    # Tema e diretriz
    conteudo.append(Paragraph(f"{icone_escopo}ESCOPO DA ANÁLISE", styles['SubtituloRelatorio']))
    
    # Tabela para tema e diretriz
    escopo_dados = [
        [Paragraph("<b>Tema pesquisado:</b>", styles['TextoNormal']), 
         Paragraph(tema, styles['TextoNormal'])],
        [Paragraph("<b>Diretriz de análise:</b>", styles['TextoNormal']), 
         Paragraph(diretriz, styles['TextoNormal'])]
    ]
    
    escopo_tabela = Table(escopo_dados, colWidths=[150, 300])
    escopo_tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 1), colors.HexColor('#F0F0F0')),
        ('GRID', (0, 0), (1, 1), 0.5, colors.HexColor('#CCCCCC')),
        ('PADDING', (0, 0), (1, 1), 8),
    ]))
    
    conteudo.append(escopo_tabela)
    conteudo.append(Spacer(1, 20))
    
    # Análise Completa
    conteudo.append(Paragraph(f"{icone_analise}ANÁLISE DETALHADA", styles['SubtituloRelatorio']))
    
    # Pré-processamento do texto para melhorar a formatação
    resposta_formatada = pre_processar_texto_ia(resposta_ia)
    
    # Dividir a resposta em parágrafos e adicionar cada um
    paragrafos_resposta = resposta_formatada.split('\n')
    
    # Ignorar o primeiro parágrafo que já foi usado no sumário
    for i, p in enumerate(paragrafos_resposta):
        if i == 0 and p.strip() == primeiro_paragrafo.strip():
            continue
            
        if p.strip():
            # Verificar se é um título
            if p.isupper() or p.startswith('#'):
                # Adicionar espaço antes de novos títulos
                conteudo.append(Spacer(1, 15))
                conteudo.append(Paragraph(p, styles['SubtituloRelatorio']))
            else:
                # Verificar se o parágrafo contém dados numéricos que poderiam ser um gráfico
                import re
                numeros = re.findall(r'\d+[.,]?\d*%?', p)
                
                if len(numeros) >= 3 and ("crescimento" in p.lower() or "aumento" in p.lower() or 
                                         "percentual" in p.lower() or "comparação" in p.lower()):
                    # Criar uma tabela simples para destacar dados numéricos
                    conteudo.append(Paragraph(p, styles['TextoNormal']))
                    
                    # Exemplo de visualização de dados (barra horizontal simples)
                    dados_viz = [[n, "■" * (len(n) + 2)] for n in numeros[:5]]
                    tabela_viz = Table(dados_viz, colWidths=[80, 300])
                    tabela_viz.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, len(dados_viz)-1), colors.HexColor('#F0F0F0')),
                        ('TEXTCOLOR', (1, 0), (1, len(dados_viz)-1), colors.HexColor('#4D268C')),
                        ('ALIGN', (0, 0), (1, len(dados_viz)-1), 'LEFT'),
                        ('PADDING', (0, 0), (1, len(dados_viz)-1), 5),
                    ]))
                    conteudo.append(tabela_viz)
                else:
                    conteudo.append(Paragraph(p, styles['TextoNormal']))
    
    conteudo.append(Spacer(1, 20))
    
    # Fontes utilizadas
    if links_utilizados and len(links_utilizados) > 0:
        conteudo.append(Paragraph(f"{icone_fontes}FONTES CONSULTADAS", styles['SubtituloRelatorio']))
        
        # Tabela para fontes
        fontes_dados = []
        for i, link in enumerate(links_utilizados):
            fontes_dados.append([Paragraph(f"{i+1}.", styles['TextoNormal']), 
                                Paragraph(link, styles['TextoNormal'])])
        
        fontes_tabela = Table(fontes_dados, colWidths=[30, 420])
        fontes_tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, len(fontes_dados)-1), colors.HexColor('#F8F8F8')),
            ('GRID', (0, 0), (1, len(fontes_dados)-1), 0.5, colors.HexColor('#DDDDDD')),
            ('PADDING', (0, 0), (1, len(fontes_dados)-1), 5),
        ]))
        
        conteudo.append(fontes_tabela)
        conteudo.append(Spacer(1, 20))
    
    # Conclusão e Recomendações
    conteudo.append(Paragraph(f"{icone_conclusao}CONCLUSÕES E RECOMENDAÇÕES", styles['SubtituloRelatorio']))
    
    # Extrair último parágrafo da resposta para conclusões
    ultimo_paragrafo = resposta_formatada.split('\n\n')[-1] if '\n\n' in resposta_formatada else resposta_formatada
    
    # Destacar conclusões em uma caixa com bordas arredondadas
    conteudo.append(Paragraph(ultimo_paragrafo, styles['Destaque']))
    
    # Rodapé
    conteudo.append(Spacer(1, 30))
    
    # Linha horizontal
    conteudo.append(Paragraph("<hr/>", styles['TextoNormal']))
    
    # Rodapé com logo pequeno e copyright
    rodape_dados = [
        [Image("icon.png", width=30, height=30), 
         Paragraph("© 2025 FP&A e Orçamento - Rede Lius Agostinianos. Todos os direitos reservados.", styles['Rodape'])]
    ]
    
    rodape_tabela = Table(rodape_dados, colWidths=[40, 410])
    rodape_tabela.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (1, 0), 'MIDDLE'),
    ]))
    
    conteudo.append(rodape_tabela)
    
    # Construir o documento
    doc.build(conteudo)
    
    # Retornar o PDF como base64 para download
    pdf_bytes = buffer.getvalue()
    buffer.close()
    b64_pdf = base64.b64encode(pdf_bytes).decode()
    return b64_pdf

# Adicionar botão para gerar relatório executivo
if 'messages' in st.session_state and len(st.session_state.messages) > 0:
    # Encontrar a última resposta da IA
    ultima_resposta = None
    for msg in reversed(st.session_state.messages):
        if msg['role'] == 'assistant':
            ultima_resposta = msg['content']
            break
    
    if ultima_resposta:
        st.write("---")
        st.subheader("Relatório Executivo")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write("Gere um relatório executivo em PDF com os resultados da análise.")
        
        with col2:
            if st.button("Gerar Relatório Executivo"):
                with st.spinner("Gerando relatório executivo..."):
                    # Obter links utilizados (se disponíveis)
                    links_utilizados = []
                    try:
                        if 'links' in locals():
                            links_utilizados = links
                    except:
                        pass
                    
                    # Gerar o relatório
                    b64_pdf = gerar_relatorio_executivo(
                        tema=tema if 'tema' in locals() else "Tema não especificado",
                        diretriz=diretriz if 'diretriz' in locals() else "Diretriz não especificada",
                        resposta_ia=ultima_resposta,
                        links_utilizados=links_utilizados
                    )
                    
                    # Criar botão de download
                    nome_arquivo = f"relatorio_executivo_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                    st.download_button(
                        label="Baixar Relatório Executivo",
                        data=base64.b64decode(b64_pdf),
                        file_name=nome_arquivo,
                        mime="application/pdf",
                        key="download_relatorio_executivo"
                    )
                    
                    st.success("Relatório executivo gerado com sucesso!")
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Inicialização do analisador de sentimento
@st.cache_resource
def inicializar_analisador_sentimento():
    try:
        nltk.download('vader_lexicon', quiet=True)
        return SentimentIntensityAnalyzer()
    except Exception as e:
        st.error(f"Erro ao inicializar analisador de sentimento: {str(e)}")
        return None

# Função para analisar sentimento do texto
def analisar_sentimento(texto):
    sia = inicializar_analisador_sentimento()
    if sia:
        sentimento = sia.polarity_scores(texto)
        return sentimento
    return None


def criar_prompt_avancado(tema, diretriz, textos, imagens=None):
    """Cria um prompt avançado com chain-of-thought para análises mais profundas"""
    
    # Base do prompt
    prompt = f"""
    Analise o seguinte conjunto de notícias sobre '{tema}' e responda de acordo com a diretriz: '{diretriz}'
    
    Para realizar uma análise completa e aprofundada, siga estas etapas de raciocínio:
    
    1. COMPREENSÃO DOS FATOS:
       - Identifique os principais fatos e eventos mencionados nas notícias
       - Organize-os cronologicamente quando possível
       - Destaque dados quantitativos e estatísticas relevantes
    
    2. ANÁLISE DE CONTEXTO:
       - Considere o contexto econômico, político e social atual
       - Identifique tendências de curto e longo prazo
       - Avalie como esses eventos se relacionam com o histórico do setor
    
    3. IMPACTO PARA A REDE LIUS:
       - Analise as implicações diretas para a Rede Lius Agostinianos
       - Identifique oportunidades e ameaças específicas
       - Considere o impacto em diferentes áreas: financeira, operacional, reputacional
    
    4. CENÁRIOS FUTUROS:
       - Projete 3 cenários possíveis (otimista, realista, pessimista)
       - Estime probabilidades para cada cenário
       - Sugira indicadores a serem monitorados para cada cenário
    
    5. RECOMENDAÇÕES ESTRATÉGICAS:
       - Proponha ações concretas de curto, médio e longo prazo
       - Priorize as recomendações por impacto e viabilidade
       - Sugira métricas para acompanhamento dos resultados
    
    Textos para análise:
    {textos[:8000]}
    """
    
    # Adiciona descrição de imagens se disponíveis
    if imagens and len(imagens) > 0:
        prompt += "\n\nImagens relevantes encontradas nas notícias:\n"
        for i, img in enumerate(imagens):
            prompt += f"{i+1}. {img.get('alt', 'Imagem sem descrição')} (URL: {img.get('url', 'N/A')})\n"
    
    return prompt