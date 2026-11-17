import streamlit as st
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