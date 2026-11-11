from pathlib import Path
import streamlit as st

supported_img_type = {
    ".png",".jpg", ".jpeg",
}
def display_uploaded_file(uploaded_files):
    for uploaded_file in uploaded_files:
        extension = Path (uploaded_file.name).suffix.lower()
        if extension in supported_img_type:
            st.image(uploaded_file, caption=uploaded_file.name)
        else:
            st.markdown( f"📎 **{uploaded_file.name}**")