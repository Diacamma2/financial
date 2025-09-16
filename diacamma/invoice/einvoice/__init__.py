from os.path import join, dirname
from locale import getlocale, setlocale, LC_ALL
from io import BytesIO

from django.utils import translation
from django.template import Template, Context

from lucterios.contacts.models import LegalEntity
from lucterios.CORE.parameters import Params
from diacamma.invoice.models import Vat
from diacamma.accounting.models import Third


def _generic_generator(template_name, bill):
    with open(join(dirname(__file__), template_name), "r", encoding="utf-8") as xml_hdl:
        template = Template(xml_hdl.read())
    return template.render(Context({
        "bill": bill,
        "seller": Third(contact=LegalEntity.objects.get(id=1)),
        "currency_code": Params.getvalue("accounting-devise-iso"),
    }))


def facturX_generator(bill):
    old_local = getlocale()
    old_language = translation.get_language()
    setlocale(LC_ALL, "C")
    translation.activate('en')
    try:
        return _generic_generator("facturX-template.xml", bill)
    finally:
        setlocale(LC_ALL, old_local)
        translation.activate(old_language)


def facturX_PDF_generator(pdf_content, bill):
    from facturx.facturx import generate_from_binary
    einvoice_content = facturX_generator(bill)
    if einvoice_content:
        pdf_content = generate_from_binary(pdf_content, einvoice_content, flavor='factur-x')
    return pdf_content


def UBL_generator(bill):
    old_local = getlocale()
    old_language = translation.get_language()
    setlocale(LC_ALL, "C")
    translation.activate('en')
    try:
        return _generic_generator("UBL-template.xml", bill)
    finally:
        setlocale(LC_ALL, old_local)
        translation.activate(old_language)


def UBL_PDF_generator(pdf_content, bill):
    from pypdf import PdfWriter, PdfReader
    einvoice_content = UBL_generator(bill)
    if einvoice_content:
        pdf_out = BytesIO()
        pdf_writer = PdfWriter(clone_from=PdfReader(stream=BytesIO(pdf_content)))
        pdf_writer.add_attachment(filename="UBL.xml", data=einvoice_content)
        pdf_writer.write_stream(pdf_out)
        pdf_content = pdf_out.getvalue()
    return pdf_content
