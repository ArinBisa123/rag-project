from pathlib import Path
from utils.img_to_content import (supported_img_type, uploaded_img_to_content)
from utils.extract_file_message import (supported_doc_type, extract_uploaded_doc )

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