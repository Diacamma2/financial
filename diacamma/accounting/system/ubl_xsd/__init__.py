'''
Created on 17 sept. 2025

@author: lag
'''
from lxml import etree
from io import BytesIO
from functools import partial
from warnings import warn
from os.path import dirname, join, isfile

prefix_ns_map = {
    # Main
    "inv": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    # Common
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    # W3C
    "xsd": "http://www.w3.org/2001/XMLSchema",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}
ubl_version_finder_xp = etree.XPath("//cbc:UBLVersionID", namespaces=prefix_ns_map)


def validateUBL(xml_content):
    tree = etree.parse(BytesIO(xml_content.encode() if hasattr(xml_content, 'encode') else xml_content))
    ubl_version = ubl_version_finder_xp(tree)
    if len(ubl_version) > 0:
        ubl_version = ubl_version[0].text.strip()
    else:
        ubl_version = "2.0"
    ubl_version_tuple = tuple([int(x) for x in ubl_version.split(".")])
    if ubl_version_tuple > (2, 1):
        warn(f"We cannot validate UBL {ubl_version} documents. Trying anyway")
        return False
    schema_path = join(dirname(__file__), "maindoc", "UBL-Invoice-2.1.xsd")
    if not isfile(schema_path):
        return False
    with open(schema_path, "rb") as stream:
        schema = etree.XMLSchema(file=stream)
    return schema.validate(tree)
