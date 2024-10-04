import os
from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm import companies
from hubspot.crm.associations import BatchInputPublicObjectId
from urllib3.util.retry import Retry
import logging
import secrets
import requests
from requests.auth import HTTPBasicAuth
from oauthlib.oauth2 import WebApplicationClient
from http_server import HTTPServer
import lxml
import lxml.builder
from lxml import etree
from lxml.etree import Element, SubElement, QName, tostring


GROOTBOEKREKENING_DEBITEUREN = "1300"


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


# get access_token from .env file
def get_access_token_hubspot():
    return os.environ["ACCESS_TOKEN"]


def get_authorisation_code_twinfield():
    CLIENT_ID = os.environ["TWINFIELD_CLIENT_ID"]
    CLIENT_SECRET = os.environ["TWINFIELD_CLIENT_SECRET"]
    REDIRECT_URI = os.environ["TWINFIELD_REDIRECT_URI"]
    AUTHORIZATION_URL = os.environ["TWINFIELD_AUTHORIZATION_URL"]
    TOKEN_URL = os.environ["TWINFIELD_TOKEN_URL"]
    COMPANY_CODE = os.environ["TWINFIELD_COMPANY_CODE"]

    httpd, address = HTTPServer()

    scope = [
        "openid",
        "twf.user",
        "twf.organisation",
        "twf.organisationUser",
        "offline_access",
    ]

    client = WebApplicationClient(CLIENT_ID)
    authorization_url = client.prepare_request_uri(
        AUTHORIZATION_URL,
        scope=scope,
        redirect_uri=REDIRECT_URI,
        nonce=secrets.token_urlsafe(),
    )

    print(f"Please go to {authorization_url} and authorize access.")
    authorization_code = input("Enter the received authorization code: ")

    auth = HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    body = client.prepare_request_body(
        code=authorization_code, redirect_uri=REDIRECT_URI
    )

    response = requests.post(TOKEN_URL, data=body, auth=auth)
    token = client.parse_request_body_response(response.text)

    os.environ["TWINFIELD_ACCESS_TOKEN"] = str(client.access_token)
    os.environ["TWINFIELD_REFRESH_TOKEN"] = str(client.refresh_token)

    return COMPANY_CODE, client.access_token


def generate_twinfield_transaction_request(
    company_code,
    access_token,
    invoice_number,
    relatie_nummer,
    total_amount,
    line_items_details,
):
    class XMLNamespaces:
        soap = "http://schemas.xmlsoap.org/soap/envelope/"
        twinfield = "http://www.twinfield.com/"

    envelope = Element(
        QName(XMLNamespaces.soap, "Envelope"),
        nsmap={"soap": XMLNamespaces.soap, "twinfield": XMLNamespaces.twinfield},
    )
    soap_header = SubElement(envelope, QName(XMLNamespaces.soap, "Header"))
    twinfield_header = SubElement(soap_header, QName(XMLNamespaces.twinfield, "Header"))
    SubElement(twinfield_header, QName(XMLNamespaces.twinfield, "AccessToken")).text = (
        access_token
    )
    SubElement(twinfield_header, QName(XMLNamespaces.twinfield, "CompanyCode")).text = (
        company_code
    )
    soap_body = SubElement(envelope, QName(XMLNamespaces.soap, "Body"))
    process_xml_document = SubElement(
        soap_body, QName(XMLNamespaces.twinfield, "ProcessXmlDocument")
    )
    xml_request = SubElement(
        process_xml_document, QName(XMLNamespaces.twinfield, "xmlRequest")
    )
    transactions = SubElement(xml_request, "transactions")
    transaction = SubElement(transactions, "transaction")
    transaction.set("destiny", "final")
    transaction.set("autobalancevat", "false")
    transaction.set("raisewarning", "false")
    header = SubElement(transaction, "header")
    SubElement(header, "office").text = company_code
    SubElement(header, "code").text = "VRK"
    SubElement(header, "period")
    SubElement(header, "date")
    SubElement(header, "currency").text = "EUR"
    SubElement(header, "invoicenumber").text = invoice_number
    SubElement(header, "duedate")
    lines = SubElement(transaction, "lines")
    line_id = 1
    line_total = SubElement(lines, "line")
    line_total.set("type", "total")
    line_total.set("id", str(line_id))
    line_id += 1
    SubElement(line_total, "value").text = str(total_amount)
    SubElement(line_total, "debitcredit").text = "debit"
    SubElement(line_total, "dim1").text = GROOTBOEKREKENING_DEBITEUREN
    SubElement(line_total, "dim2").text = relatie_nummer
    for line_item in line_items_details:
        line_detail = SubElement(lines, "line")
        line_detail.set("type", "detail")
        line_detail.set("id", str(line_id))
        line_id += 1
        SubElement(line_detail, "value").text = str(line_item.amount)
        SubElement(line_detail, "debitcredit").text = "credit"
        SubElement(line_detail, "dim1").text = line_item.grootboek
        SubElement(line_detail, "dim2").text = line_item.kostenplaats
        SubElement(line_detail, "description").text = line_item.name
        SubElement(line_detail, "vatcode").text = "VN"
        SubElement(line_detail, "vatvalue").text = 0
    return envelope


request = generate_twinfield_transaction_request("CC", "AC", "123456", "5432", 1234, [])
xml = etree.tostring(request, pretty_print=True)
print(xml.decode(), end="")

retry = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
)
api_client = HubSpot(retry=retry)

api_client.access_token = get_access_token_hubspot()

# all_companies = api_client.crm.companies.get_all()

# print(all_companies)

api = api_client.crm.invoices.basic_api

api_line_items = api_client.crm.line_items.basic_api
api_companies = api_client.crm.companies.basic_api

twinfield_company_code, twinfield_access_token = get_authorisation_code_twinfield()
print(f"Access token: {twinfield_access_token}")

invoices_details = api.get_crm_v3_objects_invoices(
    properties=[
        "hs_invoice_status",
        "hs_amount_billed",
        "hs_balance_due",
        "hs_due_date",
        "hs_number",
    ]
)

for invoice in invoices_details.results:
    invoice_status = invoice.properties["hs_invoice_status"]
    invoice_number = invoice.properties["hs_number"]
    logger.info(
        f"retrieved invoice {invoice_number}[{invoice.id}] with status {invoice_status}"
    )
    if invoice_status != "paid":
        logger.info(f"skipping invoice {invoice_number}[{invoice.id}]")
        continue

    batch_ids = BatchInputPublicObjectId([{"id": invoice.id}])
    invoice_companies = api_client.crm.associations.batch_api.read(
        from_object_type="invoice",
        to_object_type="companies",
        batch_input_public_object_id=batch_ids,
    )
    invoice_companies_dict = invoice_companies.to_dict()
    if (
        "num_errors" in invoice_companies_dict
        and invoice_companies_dict["num_errors"] > 0
    ):
        logger.error(f"{invoice_companies_dict['errors'][0]['message']}")
        continue
    company_id = invoice_companies.results[0].to[0].id
    company = api_companies.get_by_id(
        company_id=company_id, properties=["relatie_nummer", "name"]
    )
    logger.info(f"company {company.properties['name']}[{company.id}] was retrieved")
    if "relatie_nummer" not in company.properties:
        logging.error(f"{company.name} does not have a relation number")
        continue
    company_relatienummer = company.properties["relatie_nummer"]

    invoice_line_items = api_client.crm.associations.batch_api.read(
        from_object_type="invoice",
        to_object_type="line_items",
        batch_input_public_object_id=batch_ids,
    )

    for items in invoice_line_items.results:
        line_items_details = [
            api_line_items.get_by_id(
                line_item_id=line_item.id,
                properties=[
                    "amount",
                    "quantity",
                    "voorraadnummer",
                    "name",
                    "kostenplaats",
                    "grootboek",
                    "gewicht",
                    "artikelsoort",
                    "artikelgroep",
                ],
            )
            for line_item in items.to
        ]
    print(line_items_details)

    twinfield_xml = generate_twinfield_transaction_request(
        twinfield_company_code, twinfield_access_token, invoice_number
    )
    print(lxml.etree.tostring(twinfield_xml, pretty_print=True))
