from auth.auth import get_access_token
from doc_source.sharepoint import get_sharepoint_metadata
from dotenv import load_dotenv
import os

load_dotenv(override=True)
sharepoint_url = os.getenv("SHAREPOINT_SITE_URL")
# SHAREPOINT_SITE_URL = ("https://testgys2024.sharepoint.com/sites/TEST-RAG/Company%20Policy/Forms/AllItems.aspx?id=%2Fsites%2FTEST%2DRAG%2FCompany%20Policy%2FSurat%20Keputusan%20Direksi&viewid=ecd4c4c4%2D900f%2D47ef%2D88b4%2D11d4bdeb034a ")
token = get_access_token()
print("Resolving sharepoint file content...")
metadata, content = get_sharepoint_metadata(sharepoint_url, token)

print("Sharepoint folder metadata")
for key, value in metadata.items():
    print(f"{key}: {value}")