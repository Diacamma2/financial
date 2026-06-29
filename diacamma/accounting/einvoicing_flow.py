'''
Created on 2026 Jun 29

@author: lag
'''
from requests import request
import json

from django.utils.translation import gettext_lazy as _

DEFAULT_CONFIG = [
    {"id": 0, 'name': None, 'flow_url': '', 'auth_url': ''},
    {"id": -1, 'name': _('Customize'), 'flow_url': '', 'auth_url': ''},
    {"id": 1, 'name': "SuperPDP", 'flow_url': 'https://api.superpdp.tech/afnor-flow', 'auth_url': 'https://api.superpdp.tech/oauth2/token'}
]


def extract_config(config_id):
    for default_item in DEFAULT_CONFIG:
        if default_item['id'] == config_id:
            return {'flow_url': default_item['flow_url'], 'auth_url': default_item['auth_url']}
    return {}


class EInvoicingFlow(object):

    http_timeout = 30

    def __init__(self, flow_url, auth_url, client_id, secret_id, **kwarg):
        self.flow_url = flow_url
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

    def _request(self, method, path, params=None, json=None, data=None, files=None, retry_on_401=True):
        url = f"{self.flow_url}{path}"
        headers = self.get_headers()
        if json is not None and files is None:
            headers["Content-Type"] = "application/json"
        response = request(method, url, headers=headers,
                           params=params, json=json, data=data, files=files)
        if response.status_code == 401 and retry_on_401:
            self.invalidate_token()
            return self._request(method, path, params=params,
                                 json=json, data=data, files=files, retry_on_401=False)
        response.raise_for_status()
        return response

    def submit_flow(self, file_content, file_name, flow_syntax,
                    processing_rule=None, flow_type=None, tracking_id=None, sha256=None):
        flow_info = {"flowSyntax": flow_syntax, "name": file_name}
        if processing_rule:
            flow_info["processingRule"] = processing_rule
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
                     tracking_id=None, limit=25):
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
        body = {"limit": limit, "where": where}
        response = self._request("POST", "/v1/flows/search", json=body)
        return response.json()

    def get_flow(self, flow_id, doc_type="Metadata"):
        response = self._request("GET", f"/v1/flows/{flow_id}", params={"docType": doc_type})
        if doc_type == "Metadata":
            return response.json()
        return response.content

    def healthcheck(self):
        response = self._request("GET", "/v1/healthcheck")
        try:
            return response.json()
        except Exception:
            return {"status": "ok", "http_status": response.status_code}
