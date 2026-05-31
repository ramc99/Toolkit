from dataclasses import dataclass, field
from flask import Blueprint, render_template, request, make_response

invoice_bp = Blueprint("invoice", __name__, url_prefix="/invoice")


@dataclass
class LineItem:
    description: str
    qty: float
    unit_price: float

    @property
    def total(self):
        return self.qty * self.unit_price


@dataclass
class InvoiceData:
    sender_name: str
    sender_email: str
    sender_phone: str
    sender_address: str
    client_name: str
    client_email: str
    client_address: str
    invoice_number: str
    date: str
    due_date: str
    items: list
    tax_rate: float = 0.0
    notes: str = ""
    template: str = "classic"

    @property
    def subtotal(self):
        return sum(i.total for i in self.items)

    @property
    def tax_amount(self):
        return self.subtotal * self.tax_rate / 100

    @property
    def grand_total(self):
        return self.subtotal + self.tax_amount


TEMPLATES = {
    "classic": "invoices/classic.html",
    "modern":  "invoices/modern.html",
}

_SAMPLE = InvoiceData(
    sender_name="Your Business",
    sender_email="hello@yourbusiness.com",
    sender_phone="+1 555 000 0000",
    sender_address="123 Main St, City, State 10001",
    client_name="Acme Corp",
    client_email="accounts@acme.com",
    client_address="456 Client Ave, New York, NY 10002",
    invoice_number="INV-0001",
    date="May 31, 2026",
    due_date="Jun 30, 2026",
    items=[
        LineItem("Web Development — Homepage redesign", 1, 2500.00),
        LineItem("SEO Audit & Report", 1, 750.00),
        LineItem("Monthly Maintenance (hours)", 5, 150.00),
    ],
    tax_rate=10.0,
    notes="Payment due within 30 days. Bank transfer details on file.",
    template="classic",
)


def _to_ctx(data: InvoiceData) -> dict:
    return {
        "sender_name":    data.sender_name,
        "sender_email":   data.sender_email,
        "sender_phone":   data.sender_phone,
        "sender_address": data.sender_address,
        "client_name":    data.client_name,
        "client_email":   data.client_email,
        "client_address": data.client_address,
        "invoice_number": data.invoice_number,
        "date":           data.date,
        "due_date":       data.due_date,
        "items":          [{"description": i.description, "qty": i.qty, "unit_price": i.unit_price, "total": i.total} for i in data.items],
        "tax_rate":       data.tax_rate,
        "tax_amount":     data.tax_amount,
        "subtotal":       data.subtotal,
        "grand_total":    data.grand_total,
        "notes":          data.notes,
    }


def render_invoice_html(data: InvoiceData) -> str:
    tpl = TEMPLATES.get(data.template, TEMPLATES["classic"])
    return render_template(tpl, **_to_ctx(data))


def generate_pdf(html: str) -> bytes:
    from weasyprint import HTML
    return HTML(string=html).write_pdf()


def _parse_form(form) -> InvoiceData:
    descs  = form.getlist("item_desc")
    qtys   = form.getlist("item_qty")
    prices = form.getlist("item_price")
    items = [
        LineItem(description=descs[i], qty=float(qtys[i] or 0), unit_price=float(prices[i] or 0))
        for i in range(len(descs))
        if descs[i].strip()
    ]
    return InvoiceData(
        sender_name=form.get("sender_name", ""),
        sender_email=form.get("sender_email", ""),
        sender_phone=form.get("sender_phone", ""),
        sender_address=form.get("sender_address", ""),
        client_name=form.get("client_name", ""),
        client_email=form.get("client_email", ""),
        client_address=form.get("client_address", ""),
        invoice_number=form.get("invoice_number", ""),
        date=form.get("date", ""),
        due_date=form.get("due_date", ""),
        items=items,
        tax_rate=float(form.get("tax_rate", 0) or 0),
        notes=form.get("notes", ""),
        template=form.get("template", "classic"),
    )


@invoice_bp.get("/")
def index():
    sample_html = render_invoice_html(_SAMPLE)
    return render_template("invoice_index.html", templates=list(TEMPLATES.keys()), sample_html=sample_html)


@invoice_bp.post("/preview")
def preview():
    try:
        data = _parse_form(request.form)
    except Exception as e:
        return str(e), 422
    return render_invoice_html(data)


@invoice_bp.post("/download")
def download():
    try:
        data = _parse_form(request.form)
    except Exception as e:
        return str(e), 422
    html = render_invoice_html(data)
    pdf = generate_pdf(html)
    fname = f"{data.invoice_number or 'invoice'}.pdf"
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'attachment; filename="{fname}"'
    return resp
