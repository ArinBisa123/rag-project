from auth.auth import get_access_token
import base64
import json

token=get_access_token()
print(f"login successful, access token obtained")
# def inspect_token(token):
#     payload = token.split(".")[1]

#     payload += "=" * (-len(payload) % 4)

#     decoded = base64.urlsafe_b64decode(payload)

#     data = json.loads(decoded)

#     print("Audience:", data.get("aud"))
#     print("Scopes:", data.get("scp"))
# inspect_token(token)
