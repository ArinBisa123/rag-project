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