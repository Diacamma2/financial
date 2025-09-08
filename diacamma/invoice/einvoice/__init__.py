from os.path import join, dirname
from locale import getlocale, setlocale, LC_ALL

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
