import msal
import os  
from dotenv import load_dotenv

load_dotenv()
client_id = os.getenv("MICROSOFT_ENTRA_CLIENT_ID")
tenant_id = os.getenv("MICROSOFT_ENTRA_tenant_id")

authority_url = f"https://login.microsoftonline.com/{tenant_id}"

scopes = ["Sites.Read.All","Files.Read"]

import os
import msal

from dotenv import load_dotenv


load_dotenv(override=True)

tenant_id = os.getenv("MICROSOFT_ENTRA_TENANT_ID")
client_id = os.getenv("MICROSOFT_ENTRA_CLIENT_ID")
# print("CLIENT_ID:", client_id)
# print("TENANT_ID:", tenant_id)
AUTHORITY = (
    f"https://login.microsoftonline.com/{tenant_id}"
)

SCOPES = [
    "Sites.Read.All",
    "Files.Read"
]


def get_access_token():

    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=AUTHORITY
    )

#    check if there are any cached accounts
    accounts = app.get_accounts()

    if accounts:

        result = app.acquire_token_silent(
            scopes=SCOPES,
            account=accounts[0]
        )

        if result and "access_token" in result:
            return result["access_token"]

    flow = app.initiate_device_flow(
        scopes=SCOPES
    )

    if "user_code" not in flow:
        raise Exception(
            f"Failed to create device flow: {flow}"
        )

    print(flow["message"])

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:

        raise Exception(
            "Login failed: "
            + result.get(
                "error_description",
                str(result) 
            )
        )

    return result["access_token"]