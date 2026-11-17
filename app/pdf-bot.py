from pathlib import Path
import streamlit as st
from langchain_chroma import Chroma
from langchain_google_genai import (GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI)
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from utils.show_attachment import display_uploaded_file
from sources.database.query_tools import (CLAIM_TOOLS)
from utils.database_runner import run_database_tools
from utils.format_docs import format_docs
from utils.clean_response_gemini import clean_response_gemini
from utils.show_sources import show_sources
from utils.process_uploaded_files import process_uploaded_files

load_dotenv(override=True)
chroma_dir = Path("./chroma_db")
collection_name = "sharepoint_docs"
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
    database_tool = llm.bind_tools(CLAIM_TOOLS)
    database_tool_map ={
        database_tool.name:database_tool for database_tool in CLAIM_TOOLS
    }
except Exception as e:
    st.error(f"Failed to initialize resources: {e}")
    st.stop()

retriever = vector_db.as_retriever(search_kwargs={"k": 4})
template = """
You are a helpful assistant that answers questions using the available company knowledge and user attachments.
Use the following sources:
1. Sharepoint knowledge: {sharepoint_context}
2. Employee and medical claim database: {database_context}
3. User attachments: {attachment_context}

Instructions:
1. Use SharePoint context for company policies, benefit rules, eligibility, and claim limits.
2. Use uploaded document content when relevant
3. Use database information for employee and transaction facts.
3. Analyze uploaded image when provided
4. Clearly distinguish information from company knowledge, database, and information from user attachments
5. If the answer cannot be found in the provided context or attachments, say that you do not know
6. Do not invent information like  employee records, claim amounts, dates,
    claim history, or policy limits.
7. Keep the answer concise and factual.

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
                database_context = run_database_tools(user_question=user_question, tool_model=database_tool, tool_map=database_tool_map)
                sharepoint_context= format_docs(retrieved_docs)
                (attachment_context,image_context)=process_uploaded_files(uploaded_files)
                # prompting
                final_prompt=prompt.format(
                    sharepoint_context=sharepoint_context,
                    database_context=database_context,
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