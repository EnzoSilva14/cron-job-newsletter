from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from pymongo import MongoClient
from models.schema import NewsLink
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGODB_ATLAS_CLUSTER_URI = os.getenv('MONGODB_URI')

def extract_link(doc: str):
    # Configuração do LLM
    llm = ChatOpenAI(temperature=0.05, model="gpt-4o-mini", api_key=OPENAI_API_KEY)

    # Prompt
    system = """Você vai receber o código HTML de uma página de notícias. Extraia todos os links de notícias que seguem o formato https://braziljournal.com/nome-da-noticia/."""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Código HTML da página: {html}"),
        ]
    )

    # Chain
    llm_with_tools = llm.bind_tools([NewsLink])
    chain_structured = prompt | llm_with_tools 

    return chain_structured.invoke({ "html": doc })

def estrutura_noticia(noticia_doc):
    # Prompt 
    system = """Você vai receber o texto de uma notícia do Brazil Journal. Extraia o título e o corpo da notícia. 
    Remova qualquer informação que não seja o título ou o corpo da notícia.
    Mantenha o título e o corpo da notícia em parágrafos separados, sem nenhuma alteração no texto.
    """
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Texto da notícia: {texto}"),
        ]
    )
    llm = ChatOpenAI(temperature=0.05, model="gpt-4o-mini", api_key=OPENAI_API_KEY)
    chain = prompt | llm | StrOutputParser()

    return chain.invoke({ "texto": noticia_doc.page_content})

def main():
    try:
        # Carregar o HTML da página de economia
        urls = ["https://braziljournal.com/economia/"]
        loader = AsyncHtmlLoader(urls)
        docs = loader.load()

        # Extrair links das notícias
        lista = extract_link(docs[0].page_content)
        links = []
        for tool_call in lista.additional_kwargs["tool_calls"]:
            arguments = tool_call["function"]["arguments"]
            link = eval(arguments)["link"]  # Converte a string JSON em um dicionário e acessa o link
            links.append(link)

        # Carregar o conteúdo das notícias
        loader = AsyncHtmlLoader(links)
        noticias_docs = loader.load()

        # Transformar HTML em texto
        html2text = Html2TextTransformer()
        docs_transformed = html2text.transform_documents(noticias_docs)

        # Estruturar as notícias
        noticias = []
        for noticia in docs_transformed:
            noticias.append(estrutura_noticia(noticia))

        json_output = []
        for i in range (len(links)):
            json_output.append({"text" : noticias[i], "link" : link[i]})
        
        # Inserir no MongoDB
        with MongoClient(MONGODB_ATLAS_CLUSTER_URI) as client:
            db = client["poc-nero"]
            noticias_collection = db["noticias"]
            noticias_collection.insert_many(json_output)

        print("Notícias processadas e salvas no MongoDB com sucesso!")

    except Exception as e:
        print(f"Erro durante a execução: {e}")
    

if __name__ == "__main__":
    main()