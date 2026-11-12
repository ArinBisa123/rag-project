from urllib.parse import urlparse, parse_qs, unquote, quote
import requests
from dotenv import load_dotenv
import os

load_dotenv(override=True)
GRAPH_BASE_URL = os.getenv("GRAPH_BASE_URL")

def graph_get(url, headers, error_message):
    response = requests.get(url, headers=headers)

    if not response.ok:
        raise RuntimeError(
            f"{error_message}\n"
            f"Status code: {response.status_code}\n"
            f"Response: {response.text}"
        )

    return response.json()


def extract_sharepoint_path(sharepoint_url):

    parsed_url = urlparse(sharepoint_url)

    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Hostname not found in SharePoint URL.")

    query_params = parse_qs(parsed_url.query)

    # Format 1:
    # /Forms/AllItems.aspx?id=/sites/TEST-RAG/Company Policy/Folder
    if "id" in query_params:
        full_path = unquote(query_params["id"][0])

    # Format 2:
    # /:f:/r/sites/TEST-RAG/Company Policy/Folder
    elif parsed_url.path.startswith("/:f:/r/"):
        full_path = unquote(
            parsed_url.path.replace("/:f:/r", "", 1)
        )

    # Opsional: link file menggunakan :x:, :w:, :b:, dan sejenisnya
    elif parsed_url.path.startswith(("/:x:/r/", "/:w:/r/", "/:b:/r/", "/:p:/r/")):
        path_parts = parsed_url.path.split("/r/", 1)

        if len(path_parts) != 2:
            raise ValueError(
                " Cannot retrieve path from SharePoint sharing URL."
            )

        full_path = "/" + unquote(path_parts[1])

    else:
        raise ValueError(
            "URL format not supported. "
            "Please use URL in the format 'Forms/AllItems.aspx?id=...' "
            "or sharing URL '/:f:/r/sites/...'"
        )

    full_path = "/" + full_path.strip("/")

    return hostname, full_path


def get_sharepoint_metadata(sharepoint_url, access_token):
    """
    Returns:
        metadata: informasi site, drive, dan folder/file
        content: daftar child item jika target merupakan folder
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    hostname, full_path = extract_sharepoint_path(sharepoint_url)

    print(f"Hostname: {hostname}")
    print(f"Full SharePoint path: {full_path}")

    path_parts = full_path.strip("/").split("/")

    if len(path_parts) < 3 or path_parts[0].casefold() != "sites":
        raise ValueError(
            "Invalid SharePoint path format. "
            "Expected: /sites/{site-name}/{document-library}/..."
        )

    site_name = path_parts[1]
    doc_library_name = path_parts[2]

    site_path = f"/sites/{site_name}"

    print(f"Site path: {site_path}")
    print(f"Document library: {doc_library_name}")

    # Get site id 

    site_endpoint = (
        f"{GRAPH_BASE_URL}/sites/"
        f"{hostname}:{site_path}"
    )

    site_data = graph_get(
        site_endpoint,
        headers,
        "Failed to retrieve site information."
    )

    site_id = site_data.get("id")

    if not site_id:
        raise RuntimeError(
            "Site ID not found in the response from Microsoft Graph API."
        )

    print(f"Found site. Site ID: {site_id}")

    # get all document libraries (drives) in the site

    drives_endpoint = (
        f"{GRAPH_BASE_URL}/sites/{site_id}/drives"
    )

    drives_data = graph_get(
        drives_endpoint,
        headers,
        "Failed to retrieve document libraries."
    )

    drives = drives_data.get("value", [])

    print("Available document libraries:")

    for drive in drives:
        print(
            f"- name={drive.get('name')!r}, "
            f"id={drive.get('id')!r}, "
            f"webUrl={drive.get('webUrl')!r}"
        )

    # choose document library based on name (case-insensitive match)

    normalized_library_name = doc_library_name.strip().casefold()

    selected_drive = next(
        (
            drive
            for drive in drives
            if drive.get("name", "").strip().casefold()
            == normalized_library_name
        ),
        None
    )

    if selected_drive is None:
        available_drives = [
            repr(drive.get("name"))
            for drive in drives
        ]

        raise RuntimeError(
            f"Document library {doc_library_name!r} not found. "
            f"Available drives: {available_drives}"
        )

    drive_id = selected_drive.get("id")

    print(
        "Selected document library: "
        f"{selected_drive.get('name')!r}"
    )
    print(f"Drive ID: {drive_id}")


    relative_parts = path_parts[3:]
    relative_item_path = "/".join(relative_parts)

    print(f"Relative item path: {relative_item_path!r}")

    if relative_item_path:
        encoded_relative_path = "/".join(
            quote(part, safe="")
            for part in relative_parts
        )

        item_endpoint = (
            f"{GRAPH_BASE_URL}/drives/{drive_id}"
            f"/root:/{encoded_relative_path}"
        )
    else:
        # If URL only points to the root of the document library
        item_endpoint = (
            f"{GRAPH_BASE_URL}/drives/{drive_id}/root"
        )

    item_data = graph_get(
        item_endpoint,
        headers,
        "Failed to retrieve SharePoint item."
    )

    item_id = item_data.get("id")
    item_name = item_data.get("name")

    print(f"Found item: {item_name!r}")
    print(f"Item ID: {item_id}")

    # if folder, retrieve children

    children = []

    if "folder" in item_data:
        children_endpoint = (
            f"{GRAPH_BASE_URL}/drives/{drive_id}"
            f"/items/{item_id}/children"
        )

        children_data = graph_get(
            children_endpoint,
            headers,
            "Failed to retrieve folder contents."
        )

        children = children_data.get("value", [])

        print(f"Items found in folder: {len(children)}")

    metadata = {
        "hostname": hostname,
        "site_id": site_id,
        "site_name": site_name,
        "site_path": site_path,
        "drive_id": drive_id,
        "document_library": selected_drive.get("name"),
        "relative_path": relative_item_path,
        "item_id": item_id,
        "item_name": item_name,
        "item_type": (
            "folder"
            if "folder" in item_data
            else "file"
            if "file" in item_data
            else "unknown"
        ),
        "item": item_data
    }

    return metadata, children