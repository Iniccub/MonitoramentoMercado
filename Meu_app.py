import streamlit as st
import requests
from serpapi import GoogleSearch
from bs4 import BeautifulSoup

# Configurações iniciais
st.set_page_config(
    page_title="Monitoramento de Mercado",
    page_icon="icon.png",
    layout="wide"
)

# Inicializar a sessão de estado para armazenar o histórico da conversa
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Definir variáveis globais
api_key_OpenaAI = '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'  # Substitua pela sua chave real
api_url = 'https://api.openai.com/v1/chat/completions'
headers_api = {
    'Authorization': f'Bearer {api_key_OpenaAI}',
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
    texto_GPT4o_mini = "🤖 - O o4-mini é o mais recente modelo compacto da série O. Ele é otimizado para raciocínio rápido e eficaz, com desempenho excepcionalmente eficiente em tarefas visuais e de codificação. A pesquisa é a de menor custo de todos os modelos."
    texto_GPT4o = "🤖 - O GPT-4o (“o” de “omni”) é o modelo topo de linha, versátil e altamente inteligente. Ele aceita entradas de texto e imagem e produz saídas de texto (incluindo Saídas Estruturadas). É o melhor modelo para a maioria das tarefas e mais capaz dos modelos da série O. A pesquisa tem maior custo, porém mais baixo em comparação aos modelos mais complexos."
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
    if st.button("Analisar"):
        if tema and diretriz:
            # Função para buscar notícias
            def buscar_noticias(tema, serpapi_key):
                params = {
                    'q': tema,
                    'tbm': 'nws',
                    'hl': 'pt-br',
                    'gl': 'br',
                    'api_key': serpapi_key
                }
                search = GoogleSearch(params)
                resultados = search.get_dict()
                noticias = resultados.get('news_results', [])
                links = [noticia.get('link') for noticia in noticias if noticia.get('link')]
                return links

            serpapi_key = '496c9ec55a6a44077bb35f27348da4d2d305c319d0d9e28b8a7b309e5d598f8f'  # Substitua pela sua chave real
            links = buscar_noticias(tema, serpapi_key)

            # Exibir links em uma caixa de texto
            if links:
                links_texto = '\n'.join(links)
                st.text_area("Links das notícias encontradas:", value=links_texto, height=200)
            else:
                st.write("Nenhum link encontrado.")

            # Extração de texto das notícias
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/135.0.0.0 Safari/537.36'
                )
            }
            textos = []
            for i, link in enumerate(links, start=1):
                try:
                    response = requests.get(link, headers=headers)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    paragrafos = soup.find_all('p')
                    texto = ' '.join(paragrafo.get_text() for paragrafo in paragrafos)
                    textos.append(texto)
                except requests.RequestException as e:
                    st.write(f'Erro ao acessar ou processar o link {i} ({link}): {e}')

            texto_completo = '\n\n'.join(textos)

            # Adicionar a diretriz e o texto completo ao histórico de mensagens
            st.session_state.messages.append({'role': 'user', 'content': f'Texto: {texto_completo}', 'exibir': False})
            st.session_state.messages.append({'role': 'user', 'content': f'Diretriz: {diretriz}'})

            # Enviar para API da OpenAI
            body_message = {
                'model': modelo,
                'messages': st.session_state.messages,
                'temperature': 0.2,
                'max_tokens': 4000
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

    # Permitir uma nova pergunta
    nova_pergunta = st.chat_input("Deseja continuar a análise com outra pergunta?")
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