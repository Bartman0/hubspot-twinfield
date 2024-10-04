import os
import sys
from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.associations import BatchInputPublicObjectId
from urllib3.util.retry import Retry


# get access_token from .env file
def access_token():
    load_dotenv()
    return os.environ["ACCESS_TOKEN"]


retry = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
)
api_client = HubSpot(retry=retry)

api_client.access_token = access_token()

# all_contacts = api_client.crm.contacts.get_all()

# print(all_contacts)

# all_companies = api_client.crm.companies.get_all()

# print(all_companies)

all_deals = api_client.crm.deals.get_all()

print(all_deals)

deal = [d for d in all_deals if "RKO" in d.properties["dealname"]][0]
id = deal.id

api = api_client.crm.objects.basic_api

deal_details = api.get_by_id(object_type="deal", object_id=id)

print(deal_details)

batch_ids = BatchInputPublicObjectId([{"id": id}])
deal_line_items = api_client.crm.associations.batch_api.read(
    from_object_type="deal",
    to_object_type="line_items",
    batch_input_public_object_id=batch_ids,
)

print(type(deal_line_items.results))

for items in deal_line_items.results:
    for li in items.to:
        print(li.id)
        li_details = api.get_by_id(object_type="line_item", object_id=li.id)
        print(li_details)

all_products = api_client.crm.products.get_all(properties=["kostenplaats", "grootboek"])

print(all_products)
