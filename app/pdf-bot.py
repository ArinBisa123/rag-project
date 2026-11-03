from pathlib import Path
import streamlit as st
from langchain_chroma import Chroma
from langchain_google_genai import (GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI)
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv(override=True)
chroma_dir = Path("./chroma_db")
collection_name = "sharepoint_docs"
# embeddings_model= "models/gemini-embedding-001"
# llm_model= "gemini-3.6-flash"

# set page
st.set_page_config(
    page_title="PDF Chatbot",
    page_icon="📄",
    layout="wide"
)

st.title("📄 PDF Chatbot")
st.caption("Ask questions about your PDF document")

def load_chroma():
    if not chroma_dir.exists():
        raise FileNotFoundError("Chroma DB directory not found. Please run the ingestion script first.")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    vector_db = Chroma(
        collection_name=collection_name,
        persist_directory=str(chroma_dir),
        embedding_function=GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    )
    return vector_db

def load_llm():
    return ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0,)

try:
    vector_db = load_chroma()
    llm = load_llm()
except Exception as e:
    st.error(f"Failed to initialize resources: {e}")
    st.stop()

retriever = vector_db.as_retriever(search_kwargs={"k": 4})
template = """
You are a helpful assistant that answers questions
based only on the provided SharePoint documents.

Use only the retrieved context below to answer
the user's question.

If the answer cannot be found in the context,
say that you do not know based on the available
documents.

Keep the answer concise and factual.

Context:
{context}

Question:
{question}

Answer:
"""
prompt = PromptTemplate.from_template(template)

if "messages" not in st.session_state:
    st.session_state.messages = []
for messages in st.session_state.messages:
    with st.chat_message(messages["role"]):
        st.markdown(messages["content"])

def format_docs(docs):
    return "\n\n".join(
        document.page_content
        for document in docs
    )

def clean_response_gemini(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if text:
                    texts.append(block["text"])
            elif isinstance(block, str):
                texts.append(block)
        return "\n".join(texts)
    return str(content)

def show_sources(docs):
    st.markdown("### Sources")

    displayed_sources = set()

    for document in docs:
        filename = document.metadata.get(
            "sharepoint_file_name",
            "Unknown document"
        )

        web_url = document.metadata.get(
            "sharepoint_file_web_url",
            ""
        )

        page = document.metadata.get("page")

        if page is not None:
            page_number = page + 1
            label = f"{filename} - halaman {page_number}"
        else:
            page_number = None
            label = filename

        source_key = (
            filename,
            page_number,
            web_url
        )
        if source_key in displayed_sources:
            continue

        displayed_sources.add(source_key)

        if web_url:
            st.markdown(
                f"- [{label}]({web_url})"
            )
        else:
            st.markdown(
                f"- {label}"
            )

user_question=st.chat_input("Ask anything about document")
if user_question:
    st.session_state.messages.append({
        "role":"user",
        "content":user_question,
    })
    with st.chat_message("user"):
        st.markdown(user_question)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching for document..."):
                retrieved_docs = (retriever.invoke(user_question))
                context=format_docs(retrieved_docs)
                final_prompt = prompt.format(context=context, question= user_question)
                response = llm.invoke(final_prompt)

                # clean
                answer = clean_response_gemini(response.content)
            st.markdown(answer)
            if retrieved_docs:
                with st.expander("Show source"):
                    show_sources(retrieved_docs)
            st.session_state.messages.append({
                "role":"assistant",
                "content":answer,
            })
        except Exception as error:
            st.error(
            f"Failed get answer: "
            f"{type(error).__name__}: {error}"
            )
            raise