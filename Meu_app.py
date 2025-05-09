import streamlit as st
import requests
from serpapi import GoogleSearch
from bs4 import BeautifulSoup
import concurrent.futures  # Para processamento paralelo
import time
from typing import List, Dict  # Para tipagem
import os
from dotenv import load_dotenv

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

def extrair_texto_url(url: str, headers: Dict[str, str]) -> str:
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
            
            texto_final = '\n\n'.join(textos)
            return limpar_texto(texto_final)
    except Exception as e:
        st.error(f"Erro ao extrair texto: {str(e)}")
        return ""

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
                            texto = future.result()
                            if texto:  # Só adiciona textos não vazios
                                textos.append(texto)
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