from pathlib import Path
import streamlit as st
from langchain_chroma import Chroma
from langchain_google_genai import (GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI)
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from utils.extract_file_message import (supported_doc_type, extract_uploaded_doc )
from utils.img_to_content import (supported_img_type, uploaded_img_to_content)
from utils.show_attachment import display_uploaded_file

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
# load chroma
def load_chroma():
    if not chroma_dir.exists():
        raise FileNotFoundError("Chroma DB directory not found. Please run the ingestion script first.")
    vector_db = Chroma(
        collection_name=collection_name,
        persist_directory=str(chroma_dir),
        embedding_function=GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    )
    return vector_db

def load_llm():
    return ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0,)
# init resources
try:
    vector_db = load_chroma()
    llm = load_llm()
except Exception as e:
    st.error(f"Failed to initialize resources: {e}")
    st.stop()

retriever = vector_db.as_retriever(search_kwargs={"k": 4})
template = """
You are a helpful assistant that answers questions using the available company knowledge and user attachments.
Instructions:
1. Use the SharePoint knowledge context when relevant
2. Use uploaded document content when relevant
3. Analyze uploaded image when provided
4. Clearly distinguish information from company knowledge and information frm user attachments
5. If the answer cannot be found in the provided context or attachments, say that you do not know
6. Do not invent information
7. Keep the answer concise and factual.

SharePoint knowledge context:
{sharepoint_context}

Uploaded document context:
{attachment_context}

Question:
{question}

Answer:
"""
prompt = PromptTemplate.from_template(template)

# history chat
if "messages" not in st.session_state:
    st.session_state.messages = []
for messages in st.session_state.messages:
    with st.chat_message(messages["role"]):
        st.markdown(messages["content"])
# helper format docs
def format_docs(docs):
    if not docs:
        return "No relevant documents were retrieved"
    formatted_documents = []
    for index, document in enumerate(docs, start=1):
        file_name= document.metadata.get("sharepoint_file_name", "Unknown document")
        page = document.metadata.get("page")
        if page is not None:
            source_label = (
                f"{file_name}, page {page + 1}"
            )
        else:
            source_label = file_name
        formatted_documents.append(
            "\n".join([
                f"[Source {index}: {source_label}]",
                document.page_content
            ])
        )
    return "\n\n".join(formatted_documents)
# helper clean response gemini
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
# helper show sources
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
# helper attachment
def process_uploaded_files(uploaded_files):
    attachment_context_parts=[]
    image_context = []
    for uploaded_file in uploaded_files:
        extension = Path(uploaded_file.name).suffix.lower()
        if extension in supported_doc_type:
            extracted_text= extract_uploaded_doc(uploaded_file)
            if extracted_text.strip():
                attachment_context_parts.append("\n".join(
                    [(
                        f"uploaded document:{uploaded_file.name}"
                    ), f"document content:{extracted_text}"]
                ))
            else:
                attachment_context_parts.append("\n".join(
                                    [(
                                        f"uploaded document:{uploaded_file.name}"
                                    ), ("no readable text was extracted from this document")]
                                ))
        elif extension in supported_img_type:
            image_block = uploaded_img_to_content(uploaded_file)
            image_context.append(image_block)
        else:
            raise ValueError(f"Unsupported format:{uploaded_file.name}")
    attachment_context= "\n\n".join(attachment_context_parts)
    if not attachment_context:
        attachment_context=("No file attachment was provided")
    return attachment_context,image_context

# chat input
user_input=st.chat_input("Ask anything about document", accept_file="multiple", max_upload_size=20)
if user_input:
    user_question = (
        user_input.text.strip()
        if user_input.text else ""
    )
    uploaded_files = list (user_input.files or [])
    if not user_question and not uploaded_files:
        st.warning("Enter a question or attach at least one file")
        st.stop()
    if not user_question:
        user_question = (
            "Analyze the uploaded attachment and explain the important information"
        )
    attachment_names = [
        uploaded_file.name for uploaded_file in uploaded_files
    ]
    history_content= user_question
    if attachment_names:
        history_content += (
            "\n\nAttachments: "+", ".join(attachment_names)
        )
    # display user message
    st.session_state.messages.append(
        {"role":"user",
            "content": history_content,
        }
    )
    with st.chat_message ("user"):
        st.markdown(user_question)
        if uploaded_files:
            display_uploaded_file(uploaded_files)
    # generate answer
    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                retrieved_docs = retriever.invoke(user_question)
                sharepoint_context= format_docs(retrieved_docs)
                (attachment_context,image_context)=process_uploaded_files(uploaded_files)
                # prompting
                final_prompt=prompt.format(
                    sharepoint_context=sharepoint_context,
                    attachment_context=attachment_context,
                    question= user_question
                )
                message_content=[{
                    "type":"text",
                    "text":final_prompt
                }]
                message_content.extend(image_context)
                message = HumanMessage(content= message_content)

                response = llm.invoke([message])
                answer= clean_response_gemini(response.content)

                # show answer
                st.markdown(answer)
                if retrieved_docs:
                    with st.expander("Show"):
                        show_sources(retrieved_docs)
                st.session_state.messages.append({
                    "role":"assitant",
                    "content":answer,
                })
        except Exception as e:
            st.error(f"Failed to process message:{type(e).__name__}:{e}")
            raise