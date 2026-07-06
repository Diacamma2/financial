'''
Created on 2026 Jun 29

@author: lag
'''
from requests import request
from abc import ABC
from requests.exceptions import HTTPError
import json

from lucterios.CORE.parameters import Params
from django.utils.translation import gettext_lazy as _

DEFAULT_CONFIG = [
    {"id": 0, 'name': None, 'flow_url': '', "directory_url": "", 'auth_url': ''},
    {"id": -1, 'name': _('Customize'), 'flow_url': '', "directory_url": "", 'auth_url': ''},
    {"id": 1, 'name': "SuperPDP", 'flow_url': 'https://api.superpdp.tech/afnor-flow', "directory_url": "https://api.superpdp.tech/afnor-directory", 'auth_url': 'https://api.superpdp.tech/oauth2/token'}
]


def extract_config(config_id):
    for default_item in DEFAULT_CONFIG:
        if default_item['id'] == config_id:
            return {'flow_url': default_item['flow_url'], 'auth_url': default_item['auth_url']}
    return {}


def get_einvoice_config(xfer=None):
    config = json.loads(Params.getvalue('accounting-einvoicing-conf'))
    if xfer is not None:
        type_changed = xfer.getparam("einvoice_type") != config.get("einvoice_type")
        config = {
            "einvoice_type": xfer.getparam("einvoice_type", config.get("einvoice_type", 0)),
            "flow_url": xfer.getparam("flow_url", config.get("flow_url", "")),
            "directory_url": xfer.getparam("directory_url", config.get("directory_url", "")),
            "auth_url": xfer.getparam("auth_url", config.get("auth_url", "")),
            "client_id": xfer.getparam("client_id", config.get("client_id", "")),
            "secret_id": xfer.getparam("secret_id", config.get("secret_id", "")),
        }
    else:
        type_changed = False
    return config, type_changed


def get_einvoicing_flow(xfer=None):
    config, _changed = get_einvoice_config(xfer)
    return EInvoicingFlow(**config)


def get_einvoicing_directory(xfer=None):
    config, _changed = get_einvoice_config(xfer)
    return EInvoicingDirectory(**config)


class EInvoicingAbstract(ABC):

    http_timeout = 30

    def __init__(self, base_url, auth_url, client_id, secret_id, **kwarg):
        self.base_url = base_url
        self.auth_url = auth_url
        self.client_id = client_id
        self.secret_id = secret_id
        self._access_token = None

    @property
    def access_token(self):
        if self._access_token is None:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.secret_id,
            }
            response = request("POST", self.auth_url, data=data)
            response.raise_for_status()
            payload = response.json()
            self._access_token = payload.get("access_token")
        return self._access_token

    def invalidate_token(self):
        self._access_token = None

    def get_headers(self):
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        return headers

    def _request(self, method, path, params=None, json=None, data=None, files=None, retry_on_401=True, raise_error=True):
        try:
            url = f"{self.base_url}{path}"
            headers = self.get_headers()
            if json is not None and files is None:
                headers["Content-Type"] = "application/json"
            response = request(method, url, headers=headers,
                               params=params, json=json, data=data, files=files)
            if response.status_code == 401 and retry_on_401:
                self.invalidate_token()
                return self._request(method, path, params=params,
                                     json=json, data=data, files=files, retry_on_401=False)
            if raise_error:
                response.raise_for_status()
            return response
        except HTTPError as err:
            print('response->content', err.response.content)
            raise

    def healthcheck(self):
        response = self._request("GET", "/v1/healthcheck")
        try:
            return response.json()
        except Exception:
            return {"status": "ok", "http_status": response.status_code}


class EInvoicingFlow(EInvoicingAbstract):

    def __init__(self, flow_url, auth_url, client_id, secret_id, **kwarg):
        super().__init__(flow_url, auth_url, client_id, secret_id, **kwarg)

    def submit_flow(self, file_content, file_name, flow_syntax,
                    processing_rule=None, flow_profile=None, flow_type=None, tracking_id=None, sha256=None):
        flow_info = {"flowSyntax": flow_syntax, "name": file_name}
        if processing_rule:
            flow_info["processingRule"] = processing_rule
        if flow_profile:
            flow_info["flowProfile"] = flow_profile
        if flow_type:
            flow_info["flowType"] = flow_type
        if tracking_id:
            flow_info["trackingId"] = tracking_id
        if sha256:
            flow_info["sha256"] = sha256
        files = {
            "file": (file_name, file_content, "application/octet-stream"),
            "flowInfo": (None, json.dumps(flow_info), "application/json"),
        }
        response = self._request("POST", "/v1/flows", files=files)
        return response.json()

    def search_flows(self, processing_rule=None, flow_type=None, status=None,
                     flow_direction=None, ack_status=None, updated_after=None, updated_before=None,
                     tracking_id=None,
                     ignore=0, limit=25):
        where = {}
        if processing_rule:
            where["processingRule"] = (
                processing_rule if isinstance(processing_rule, list) else [processing_rule]
            )
        if flow_type:
            where["flowType"] = flow_type if isinstance(flow_type, list) else [flow_type]
        if status:
            where["status"] = status if isinstance(status, list) else [status]
        if flow_direction:
            where["flowDirection"] = (
                flow_direction if isinstance(flow_direction, list) else [flow_direction]
            )
        if ack_status:
            where["ackStatus"] = ack_status
        if updated_after:
            where["updatedAfter"] = updated_after
        if updated_before:
            where["updatedBefore"] = updated_before
        if tracking_id:
            where["trackingId"] = tracking_id
        body = {"ignore": ignore, "limit": limit, "where": where}
        response = self._request("POST", "/v1/flows/search", json=body)
        return response.json()

    def get_flow(self, flow_id, doc_type="Metadata"):
        response = self._request("GET", f"/v1/flows/{flow_id}", params={"docType": doc_type})
        if doc_type == "Metadata":
            return response.json()
        return response.content


class EInvoicingDirectory(EInvoicingAbstract):

    def __init__(self, directory_url, auth_url, client_id, secret_id, **kwarg):
        super().__init__(directory_url, auth_url, client_id, secret_id, **kwarg)

    def search_company(self, name=None, siren_siret=None, postalcode=None, locality=None, status=None, ignore=0, limit=50):
        body = {"limit": limit, "ignore": ignore}
        body['fields'] = ["siret", "siren", "name", "facilityType", "administrativeStatus", "siretInstructions",
                          "address", "pmStatus", "pmOnly", "managesPaymentStatus",
                          "managesLegalCommitment", "managesLegalCommitmentOrService", "serviceCodeStatus"]
        filters = {}
        if name:
            filters["name"] = {"op": "contains", "value": name}
        if siren_siret:
            if len(siren_siret) < 10:
                filters["siren"] = {"op": "strict", "value": siren_siret}
            else:
                filters["siret"] = {"op": "strict", "value": siren_siret}
        if postalcode:
            filters["postalcode"] = {"op": "contains", "value": postalcode}
        if locality:
            filters["locality"] = {"op": "contains", "value": locality}
        if status:
            filters["administrativeStatus"] = {"op": "strict", "value": status}
        if len(filters) > 0:
            body['filters'] = filters
        print(">> body", body)
        response = self._request("POST", "/v1/siret/search", json=body, raise_error=False)
        if response.status_code == 204:
            return {"total": 0, "results": [], "error": response.json()}
        elif response.status_code == 400:
            return {"total": 0, "results": [], "error": response.json()}
        return response.json()

    def get_establishment_by_siret(self, siret):
        response = self._request("GET", f"/v1/siret/code-insee:{siret}")
        return response.json()
