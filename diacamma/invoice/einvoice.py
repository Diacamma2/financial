from digitalInvoice import WriterInvoice
from io import BytesIO

from lucterios.CORE.parameters import Params
from lucterios.contacts.models import LegalEntity

from diacamma.accounting.models import Third


def generic_PDF_generator(pdf_content, bill, eformat):
    pdf_stream = BytesIO(pdf_content)
    invoice_data = {
        "bill": bill.from_einvoice(),
        "seller": Third(contact=LegalEntity.objects.get(id=1)).from_einvoice(),
        "buyer": bill.third.from_einvoice(),
        "currency_code": Params.getvalue("accounting-devise-iso"),
    }
    writer = WriterInvoice()
    writer.run(eformat=eformat, data=invoice_data)
    writer.saveInPDF(pdf_stream)
    return pdf_stream.getvalue()


def facturX_PDF_generator(pdf_content, bill):
    return generic_PDF_generator(pdf_content, bill, WriterInvoice.facturX)


def UBL_PDF_generator(pdf_content, bill):
    return generic_PDF_generator(pdf_content, bill, WriterInvoice.UBL)
