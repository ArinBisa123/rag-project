from pathlib import Path
import tempfile
import os
from langchain_community.document_loaders import (PyPDFLoader, Docx2txtLoader)

supported_doc_type = {
    ".pdf", ".docx",
}
def extract_uploaded_doc(uploaded_file):
    extension = Path (uploaded_file.name).suffix.lower()
    if extension not in supported_doc_type:
        raise ValueError(f"Unsupported document format:{extension}")
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension,) as temporary_file:
            temporary_file.write(uploaded_file.getvalue())
            temporary_path = temporary_file.name
            if extension == ".pdf":
                file_loader = PyPDFLoader(temporary_path)
            elif extension == ".docx":
                file_loader = Docx2txtLoader (temporary_path)
            documents = file_loader.load()
            extracted_text = "\n\n".join(document.page_content 
                                         for document in documents
                                            if document.page_content.strip())
            return extracted_text
    finally:
        if (temporary_path and os.path.exists(temporary_path)):
            os.remove(temporary_path)