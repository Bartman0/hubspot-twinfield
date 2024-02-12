import os
from dotenv import load_dotenv
from hubspot import HubSpot
from urllib3.util.retry import Retry


# get access_token from .env file
def access_token():
  load_dotenv()
  return os.environ['ACCESS_TOKEN']


retry = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
)
api_client = HubSpot(retry=retry)

api_client.access_token = access_token()

all_contacts = api_client.crm.contacts.get_all()

print(all_contacts)

all_companies = api_client.crm.companies.get_all()

print(all_companies)

invoice_api = api_client.crm.extensions.accounting.invoice_api
print(invoice_api.api_client.__dict__)
