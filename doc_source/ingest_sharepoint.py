import os
import shutil
import requests
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader 
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from auth.auth import get_access_token
from doc_source.sharepoint import (get_sharepoint_metadata)

load_dotenv(override=True)
graph_base_url = os.getenv("GRAPH_BASE_URL")
sharepoint_url = os.getenv("SHAREPOINT_SITE_URL")
api_key = os.getenv("GOOGLE_API_KEY")

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent
download_dir = base_dir / "temp_sharepoint"
chroma_dir = project_dir / "chroma_db"
collection_name = "sharepoint_docs"
support_file_types = {".pdf", ".docx"}

def validate_environment_variables():
    required_vars = {
        "sharepoint_url": sharepoint_url,
        "graph_base_url": graph_base_url,
        "api_key": api_key
    }
    missing_vars = [variable_name for variable_name, variable_value in required_vars.items() if not variable_value]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

def create_graph_session(access_token):
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    })
    return session

def graph_get(session, url, error_message):
    items=[]
    while url:
        response = session.get(url)
        if not response.ok:
            raise RuntimeError(f"{error_message} Status code: {response.status_code}, Response: {response.text}")   
        payload = response.json()
        items.extend(payload.get("value", []))
        url = payload.get("@odata.nextLink")
    return items

def list_folder_child(session, drive_id, folder_id):
    endpoint = ( f"{graph_base_url}/drives/{drive_id}"
        f"/items/{folder_id}/children"
        "?$select=id,name,file,folder,parentReference,"
        "webUrl,lastModifiedDateTime,size,eTag"
        "&$top=200")
    return graph_get(session=session, url=endpoint, error_message="Failed to list child items for folder.")

def find_pdf_docx_files(session, drive_id, folder_id, relative_path=""):
    pdf_docx_files = []
    child_items = list_folder_child(session=session, drive_id=drive_id, folder_id=folder_id)
    for item in child_items:
        item_name = item.get("name","")
        item_relative_path = f"{relative_path}/{item_name}".strip("/")
        item_id = item.get("id")
        if "folder" in item:
            nested_files = find_pdf_docx_files(session=session, drive_id=drive_id, folder_id=item_id, relative_path=item_relative_path)
            pdf_docx_files.extend(nested_files)
            continue
        if "file" not in item:
            continue
        extension = Path(item_name).suffix.lower()
        if extension not in support_file_types:
            print(f"Skipping unsupported file type: {item_name} (extension: {extension})")
            continue
        item["relative_path"] = (item_relative_path)
        pdf_docx_files.append(item)
    return pdf_docx_files

def clean_relative_path(relative_path):
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    path_parts =[]
    for part in Path(relative_path).parts:
        cleaned_part = part
        for char in invalid_chars:
            cleaned_part = cleaned_part.replace(char, "_")
        path_parts.append(cleaned_part)
    return Path(*path_parts)

def download_file(session, drive_id,file_item):
    file_id = file_item["id"]
    relative_path = clean_relative_path(file_item["relative_path"])
    destination_path = download_dir / relative_path
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    download_endpoint = f"{graph_base_url}/drives/{drive_id}/items/{file_id}/content"
    with session.get(download_endpoint, stream=True) as response:
        if not response.ok:
            raise RuntimeError(
                f"Failed to download file: {file_item['name']}. "
                f"Status code: {response.status_code}, Response: {response.text}"
            )
        with destination_path.open("wb") as output_file:
            for block in response.iter_content(chunk_size=1024 * 1024):  # 1 MB chunks
                if block:
                    output_file.write(block)
    return destination_path

def load_file(local_path, file_item, drive_id):
    extension = Path(local_path).suffix.lower()
    if extension == ".pdf":
        loader = PyPDFLoader(str(local_path))
    elif extension == ".docx":
        loader = Docx2txtLoader(str(local_path))
    else:
        raise ValueError(f"Unsupported file type: {extension}") 
    documents = loader.load()
    for doc in documents:
        doc.metadata.update({
            "source type": "sharepoint",
            "file_type": extension,
            "sharepoint_drive_id": drive_id,
            "sharepoint_file_id": file_item["id"],
            "sharepoint_file_name": file_item["name"],
            "sharepoint_file_relative_path": file_item["relative_path"],
            "sharepoint_file_web_url": file_item.get("webUrl"),
            "sharepoint_file_last_modified": file_item.get("lastModifiedDateTime"),
        })
    return documents

def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, separators=["\n\n",
            "\n",
            ". ",
            " ",
            ""])
    chunks = splitter.split_documents(documents)
    for chunk_index, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = chunk_index
    return chunks

def embed_and_store_documents(chunks): 
    if not chunks:
        raise ValueError("No documents to embed and store.")
    if chroma_dir.exists():
        print("Removing existing Chroma DB...")
        shutil.rmtree(chroma_dir)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(chroma_dir),
        collection_name=collection_name
    )
    return vector_db
def main():
    validate_environment_variables()

    download_dir.mkdir(parents=True, exist_ok=True)
    print("Sharepoint ingestion process started...")
    print("Login to Microsoft Entra ID")
    access_token = get_access_token()
    session = create_graph_session(access_token)
    print("Resolving SharePoint folder metadata and content...")
    metadata, initial_child= get_sharepoint_metadata(sharepoint_url, access_token)
    drive_id = metadata["drive_id"]
    root_item_id = metadata["item_id"]
    root_item_type=metadata["item_type"]
    print(f"[INFO] Drive ID: {drive_id}")
    print(f"[INFO] Root item ID: {root_item_id}")
    print(f"[INFO] Item type: {root_item_type}")
    print("Finding PDF and DOCX files in the SharePoint folder...")
    if root_item_type == "folder":

        supported_files = find_pdf_docx_files(
            session=session,
            drive_id=drive_id,
            folder_id=root_item_id
        )

    elif root_item_type == "file":

        root_item = metadata["item"]

        extension = Path(
            root_item["name"]
        ).suffix.lower()

        if extension not in support_file_types:

            raise RuntimeError(
                "Unsupported file type: "
                f"{root_item['name']}"
            )

        root_item["relative_path"] = (
            root_item["name"]
        )

        supported_files = [
            root_item
        ]

    else:

        raise RuntimeError(
            "Root item is neither folder "
            f"nor file: {root_item_type}"
        )


    if not supported_files:

        raise RuntimeError(
            "No PDF or DOCX files found."
        )

    print(
        f"[INFO] Found "
        f"{len(supported_files)} files."
    )
    if not supported_files:
        raise RuntimeError("No PDF or DOCX files found in the SharePoint folder.")
    print(f"[INFO] Found {len(supported_files)} PDF/DOCX files.")
    print("Downloading files from SharePoint...")
    downloaded_files = []
    for number, file_item in enumerate(supported_files, start=1):
        print(f"[{number}/{len(supported_files)}] {file_item['relative_path']}")
        try:
            local_path = download_file(session=session, drive_id=drive_id, file_item=file_item)
            documents = load_file(local_path=local_path, file_item=file_item, drive_id=drive_id)
            extracted_char= sum(len(doc.page_content.strip()) for doc in documents)
            if extracted_char == 0:
                print(f"[WARNING] No text extracted from file: {file_item['relative_path']}")
                continue
            downloaded_files.extend(documents)
            print(f"[OK] {len(documents)}page, {extracted_char} characters")
        except Exception as e:
            print(f"{e}")
    if not downloaded_files:
        raise RuntimeError("No text extracted from any downloaded files.")

    print("Chunking documents...")
    chunks = chunk_documents(downloaded_files)
    print(f"Total chunks created: {len(chunks)}")
    print("Embedding and storing chunks...")
    vector_db = embed_and_store_documents(chunks)
    stored_count = vector_db._collection.count()
    print("Ingestion process completed successfully.")
    print(f"[INFO] Collection: {collection_name}")
    print(f"[INFO] Total vectors stored: {stored_count}")
if __name__ == "__main__":
    main()