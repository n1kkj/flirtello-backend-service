#
#   A tool to create a fake user and get their token for the test purposes
#

from db.lib.auth import SupabaseAuth
import os
from sqlmodel import create_engine
from dotenv import load_dotenv
from db.lib.crypto import encrypt

from supabase import create_client, Client


load_dotenv("src/.env.dev", override=True)

tg_id = 123123
email = f"{tg_id}@tg.flirtello.com"

passs = encrypt(email, os.environ.get("PASSKEY"))
print(email, passs)


engine = create_engine(os.environ.get("DB_URL")) 

auth = SupabaseAuth(
    os.environ.get("API_URL"),
    os.environ.get("SERVICE_ROLE_KEY"),
    os.environ.get("PASSKEY"),
    engine
)

auth.delete_user_by_email(email)
auth.create_normal_user(email, passs)



api_url = os.environ.get("API_URL")
srk = os.environ.get("SERVICE_ROLE_KEY")
print(api_url)
client:Client = create_client(api_url, srk)

# user = list(filter(lambda q : q.email == email, client.auth.admin.list_users()))[0]

# client.auth.admin.update_user_by_id(user.id, {"password": passs})

user = client.auth.sign_in_with_password({"email": email, 
                                   "password": passs})

token = user.session.access_token
print(token)

os._exit(0)
# print(client.from_("channels").select("*").execute())

# client2: Client = create_client(api_url, token)

# user = client.auth.get_user(token)
# print(user)