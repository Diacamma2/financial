'''
Created on 7 janv. 2026

@author: lag
'''
from io import BufferedReader, BytesIO
from pypdf import PdfReader
from lxml import etree
from datetime import datetime


def extract_xml_from_pdf(einvoice_file):
    from facturx.facturx import get_facturx_xml_from_pdf
    _filename, einvoice_xml = get_facturx_xml_from_pdf(einvoice_file)
    if not einvoice_xml:
        pdf_reader = PdfReader(stream=einvoice_file)
        for attach_obj in pdf_reader.attachment_list:
            if attach_obj.name.endswith('.xml'):
                einvoice_xml = attach_obj.content
                break
    if isinstance(einvoice_xml, bytes):
        einvoice_xml_buff = BytesIO(einvoice_xml)
        einvoice_xml_buff.content_type = 'text/xml'
    else:
        einvoice_xml_buff = None
    return einvoice_xml_buff


def default_invoice(einvoice_format):
    return {
        'format': einvoice_format,
        "bill": {
            "date": '0000-00-00',
            'num': '9999',
            'origin': '',
            'detail': [
                {
                    'reference': '',
                    'designation': '',
                    'price': '',
                    'quantity': '',
                    'vat_rate': 0,
                    'reduce': 0,
                    'total': 0,
                }
            ],
            'vat_info': [
                {
                    'calculate': 0,
                    'basic': 0,
                    'rate': 0,
                }
            ],
            'total': {
                'excltax': 0,
                'incltax': 0,
                'payed': 0,
                'topay': 0,
            },
        },
        'buyer': {
            'name': '',
            'legal_ident': '',
            'vat_ident': '',
            'postalcode': '',
            'address': '',
            'city': '',
            'country': '',
            'email': '',
            'phone': '',
        },
        "seller": {
            'name': '',
            'legal_ident': '',
            'vat_ident': '',
            'postalcode': '',
            'address': '',
            'city': '',
            'country': '',
            'email': '',
            'phone': '',
        },
        "currency_code": ''
    }


class XMLManage(object):

    def __init__(self, xml, ns):
        self.xml = xml
        self.ns = ns

    def get_value(self, name):
        values = self.xml.xpath(name, namespaces=self.ns)
        if len(values) > 0:
            return values[0]
        else:
            return ""

    def get_float(self, name):
        try:
            value = self.get_value(name)
            return float(value)
        except ValueError:
            return 0.0

    def sub_item(self, name):
        values = self.xml.xpath(name, namespaces=self.ns)
        if len(values) > 0:
            return XMLManage(values[0], self.ns)
        else:
            return None

    def get_list(self, name):
        for item in self.xml.xpath(name, namespaces=self.ns):
            yield XMLManage(item, self.ns)


def read_ubl_xml(xml_content):
    from diacamma.accounting.system.ubl_xsd import validateUBL, prefix_ns_map
    ubl_xml_tree = validateUBL(xml_content)
    if ubl_xml_tree:
        xml_mng = XMLManage(ubl_xml_tree, prefix_ns_map)
        invoice_content = default_invoice('UBL')
        invoice_content["currency_code"] = xml_mng.get_value('//cbc:DocumentCurrencyCode/text()')
        seller_party = xml_mng.sub_item('//cac:AccountingSupplierParty/cac:Party')
        invoice_content["seller"]['name'] = seller_party.get_value('cac:PartyName/cbc:Name/text()')
        invoice_content["seller"]['legal_ident'] = seller_party.get_value('cbc:EndpointID/text()')
        invoice_content["seller"]['vat_ident'] = seller_party.get_value('cac:PartyTaxScheme/cbc:CompanyID/text()')
        invoice_content["seller"]['postalcode'] = seller_party.get_value('cac:PostalAddress/cbc:PostalZone/text()')
        invoice_content["seller"]['address'] = [
            seller_party.get_value('cac:PostalAddress/cbc:StreetName/text()'),
            seller_party.get_value('cac:PostalAddress/cbc:AdditionalStreetName/text()'),
        ]
        invoice_content["seller"]['city'] = seller_party.get_value('cac:PostalAddress//cbc:CityName/text()')
        invoice_content["seller"]['country'] = seller_party.get_value('cac:PostalAddress/cac:Country/cbc:IdentificationCode/text()')
        invoice_content["seller"]['email'] = seller_party.get_value('cac:Contact/cbc:ElectronicMail/text()')
        invoice_content["seller"]['phone'] = seller_party.get_value('cac:Contact/cbc:Telephone/text()')

        buyer_party = xml_mng.sub_item('//cac:AccountingCustomerParty/cac:Party')
        invoice_content["buyer"]['name'] = buyer_party.get_value('cac:PartyName/cbc:Name/text()')
        invoice_content["buyer"]['legal_ident'] = buyer_party.get_value('cbc:EndpointID/text()')
        invoice_content["buyer"]['vat_ident'] = buyer_party.get_value('cac:PartyTaxScheme/cbc:CompanyID/text()')
        invoice_content["buyer"]['postalcode'] = buyer_party.get_value('cac:PostalAddress/cbc:PostalZone/text()')
        invoice_content["buyer"]['address'] = [
            buyer_party.get_value('cac:PostalAddress/cbc:StreetName/text()'),
            buyer_party.get_value('cac:PostalAddress/cbc:AdditionalStreetName/text()'),
        ]
        invoice_content["buyer"]['city'] = buyer_party.get_value('cac:PostalAddress//cbc:CityName/text()')
        invoice_content["buyer"]['country'] = buyer_party.get_value('cac:PostalAddress/cac:Country/cbc:IdentificationCode/text()')
        invoice_content["buyer"]['email'] = buyer_party.get_value('cac:Contact/cbc:ElectronicMail/text()')
        invoice_content["buyer"]['phone'] = buyer_party.get_value('cac:Contact/cbc:Telephone/text()')

        invoice_content["bill"]["date"] = xml_mng.get_value('//cbc:IssueDate/text()')
        invoice_content["bill"]['num'] = xml_mng.get_value('//cbc:ID/text()')
        invoice_content["bill"]['total']['excltax'] = xml_mng.get_float('//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount/text()')
        invoice_content["bill"]['total']['incltax'] = xml_mng.get_float('//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount/text()')
        invoice_content["bill"]['total']['payed'] = xml_mng.get_float('//cac:LegalMonetaryTotal/cbc:PrepaidAmount/text()')
        invoice_content["bill"]['total']['topay'] = None
        invoice_content["bill"]['vat_info'] = []
        for xml_item in xml_mng.get_list('//cac:TaxTotal/cac:TaxSubtotal'):
            new_vat_info = {
                'calculate': xml_item.get_float('cbc:TaxAmount/text()'),
                'basic': xml_item.get_float('cbc:TaxableAmount/text()'),
                'rate': xml_item.get_float('cac:TaxCategory/cbc:Percent/text()')
            }
            invoice_content["bill"]['vat_info'].append(new_vat_info)

        invoice_content["bill"]['detail'] = []
        for xml_item in xml_mng.get_list('//cac:InvoiceLine'):
            new_detail = {
                'designation': xml_item.get_value('cac:Item/cbc:Name/text()'),
                'reference': xml_item.get_value('cac:Item/cac:SellersItemIdentification/cbc:ID/text()'),
                'vat_rate': xml_item.get_float('cac:Item/cac:ClassifiedTaxCategory/cbc:Percent/text()'),
                'price': xml_item.get_float('cac:Price/cbc:PriceAmount/text()'),
                'quantity': xml_item.get_float('cac:Price/cbc:BaseQuantity/text()'),
                'reduce': xml_item.get_float('cac:Price/cac:AllowanceCharge/cbc:Amount/text()'),
                'total': xml_item.get_float('cbc:LineExtensionAmount/text()'),
            }
            invoice_content["bill"]['detail'].append(new_detail)
        return invoice_content
    else:
        return None


def read_facturx_xml(xml_content):
    from facturx.facturx import xml_check_xsd, get_flavor, get_xml_namespaces
    try:
        xml_check_xsd(xml_content)
    except Exception:
        return None
    facturx_xml = etree.fromstring(xml_content)
    flavor = get_flavor(facturx_xml)
    xml_mng = XMLManage(facturx_xml, get_xml_namespaces(flavor))
    invoice_content = default_invoice('facturX')
    invoice_content["currency_code"] = xml_mng.get_value('//rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeSettlement/ram:InvoiceCurrencyCode/text()')

    seller_party = xml_mng.sub_item('//rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeAgreement/ram:SellerTradeParty')
    invoice_content["seller"]['name'] = seller_party.get_value('ram:Name/text()')
    invoice_content["seller"]['legal_ident'] = seller_party.get_value('ram:SpecifiedLegalOrganization/ram:ID/text()')
    invoice_content["seller"]['vat_ident'] = seller_party.get_value('ram:SpecifiedTaxRegistration/ram:ID/text()')
    invoice_content["seller"]['postalcode'] = seller_party.get_value('ram:PostalTradeAddress/ram:PostcodeCode/text()')
    invoice_content["seller"]['address'] = [
        seller_party.get_value('ram:PostalTradeAddress/ram:LineOne/text()'),
        seller_party.get_value('ram:PostalTradeAddress/ram:LineTwo/text()'),
        seller_party.get_value('ram:PostalTradeAddress/ram:LineThree/text()')
    ]
    invoice_content["seller"]['city'] = seller_party.get_value('ram:PostalTradeAddress/ram:CityName/text()')
    invoice_content["seller"]['country'] = seller_party.get_value('ram:PostalTradeAddress/ram:CountryID/text()')
    invoice_content["seller"]['email'] = seller_party.get_value('ram:URIUniversalCommunication/ram:URIID/text()')
    invoice_content["seller"]['phone'] = None

    buyer_party = xml_mng.sub_item('//rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeAgreement/ram:BuyerTradeParty')
    invoice_content["buyer"]['name'] = buyer_party.get_value('ram:Name/text()')
    invoice_content["buyer"]['legal_ident'] = buyer_party.get_value('ram:SpecifiedLegalOrganization/ram:ID/text()')
    invoice_content["buyer"]['vat_ident'] = buyer_party.get_value('ram:SpecifiedTaxRegistration/ram:ID/text()')
    invoice_content["buyer"]['postalcode'] = buyer_party.get_value('ram:PostalTradeAddress/ram:PostcodeCode/text()')
    invoice_content["buyer"]['address'] = [
        buyer_party.get_value('ram:PostalTradeAddress/ram:LineOne/text()'),
        buyer_party.get_value('ram:PostalTradeAddress/ram:LineTwo/text()'),
        buyer_party.get_value('ram:PostalTradeAddress/ram:LineThree/text()')
    ]
    invoice_content["buyer"]['city'] = buyer_party.get_value('ram:PostalTradeAddress/ram:CityName/text()')
    invoice_content["buyer"]['country'] = buyer_party.get_value('ram:PostalTradeAddress/ram:CountryID/text()')
    invoice_content["buyer"]['email'] = buyer_party.get_value('ram:URIUniversalCommunication/ram:URIID/text()')
    invoice_content["buyer"]['phone'] = None

    invoice_content["bill"]["date"] = datetime.strptime(xml_mng.get_value('//rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString/text()'), "%Y%m%d").date().isoformat()
    invoice_content["bill"]['num'] = xml_mng.get_value('//rsm:ExchangedDocument/ram:ID/text()')
    invoice_content["bill"]['origin'] = xml_mng.get_value('//rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeAgreement/ram:BuyerOrderReferencedDocument/ram:IssuerAssignedID/text()')
    monetary_summation = xml_mng.sub_item('//rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeSettlement/ram:SpecifiedTradeSettlementHeaderMonetarySummation')
    invoice_content["bill"]['total']['excltax'] = monetary_summation.get_float('ram:LineTotalAmount/text()')
    invoice_content["bill"]['total']['incltax'] = monetary_summation.get_float('ram:GrandTotalAmount/text()')
    invoice_content["bill"]['total']['payed'] = monetary_summation.get_float('ram:TotalPrepaidAmount/text()')
    invoice_content["bill"]['total']['topay'] = monetary_summation.get_float('ram:DuePayableAmount/text()')
    invoice_content["bill"]['vat_info'] = []
    for xml_item in xml_mng.get_list('//rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax'):
        new_vat_info = {
            'calculate': xml_item.get_float('ram:CalculatedAmount/text()'),
            'basic': xml_item.get_float('ram:BasisAmount/text()'),
            'rate': xml_item.get_float('ram:RateApplicablePercent/text()')
        }
        invoice_content["bill"]['vat_info'].append(new_vat_info)
    invoice_content["bill"]['detail'] = []
    for xml_item in xml_mng.get_list('//rsm:SupplyChainTradeTransaction/ram:IncludedSupplyChainTradeLineItem'):
        new_detail = {
            'reference': xml_item.get_value('ram:SpecifiedTradeProduct/ram:GlobalID/text()'),
            'designation': xml_item.get_value('ram:SpecifiedTradeProduct/ram:Name/text()'),
            'price': xml_item.get_float('ram:SpecifiedLineTradeAgreement/ram:NetPriceProductTradePrice/ram:ChargeAmount/text()'),
            'quantity': xml_item.get_float('ram:SpecifiedLineTradeDelivery/ram:BilledQuantity/text()'),
            'vat_rate': xml_item.get_float('ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:RateApplicablePercent/text()'),
            'reduce': xml_item.get_float('ram:SpecifiedLineTradeSettlement/ram:SpecifiedTradeAllowanceCharge/ram:ActualAmount/text()'),
            'total': xml_item.get_float('ram:SpecifiedLineTradeSettlement/ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount/text()'),
        }
        invoice_content["bill"]['detail'].append(new_detail)

    return invoice_content


def read_file(einvoice_file):
    initial_name = einvoice_file.name
    einvoice_content = None
    if hasattr(einvoice_file, 'content_type') and einvoice_file.content_type == 'application/pdf':
        einvoice_file = extract_xml_from_pdf(BufferedReader(einvoice_file))
    if hasattr(einvoice_file, 'content_type') and einvoice_file.content_type == 'text/xml':
        einvoice_xml = einvoice_file.read()
        einvoice_content = read_ubl_xml(einvoice_xml)
        if einvoice_content is None:
            einvoice_content = read_facturx_xml(einvoice_xml)
    if einvoice_content is None:
        einvoice_content = {'error': '%s is not an e-invoice supported !' % initial_name}
    return einvoice_content
