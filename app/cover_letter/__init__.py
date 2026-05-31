from dataclasses import dataclass
from flask import Blueprint, render_template, request, make_response

cover_letter_bp = Blueprint("cover_letter", __name__, url_prefix="/cover-letter")


# ── Models ────────────────────────────────────────────────────────────────────

@dataclass
class SenderInfo:
    name: str
    email: str
    phone: str
    location: str
    linkedin: str = ""
    website: str = ""


@dataclass
class CoverLetterData:
    sender: SenderInfo
    date: str
    company: str
    job_title: str
    hiring_manager: str = ""
    opening: str = ""
    body_1: str = ""
    body_2: str = ""
    closing: str = ""
    template: str = "classic"


# ── Template registry ─────────────────────────────────────────────────────────

TEMPLATES = {
    "classic": "cover_letters/classic.html",
    "modern":  "cover_letters/modern.html",
    "minimal": "cover_letters/minimal.html",
}

_SAMPLE = CoverLetterData(
    sender=SenderInfo(
        name="Your Name",
        email="yourname@email.com",
        phone="+1 555 000 0000",
        location="City, State",
        linkedin="linkedin.com/in/yourname",
        website="",
    ),
    date="May 31, 2026",
    company="Acme Corp",
    job_title="Senior Software Engineer",
    hiring_manager="Hiring Manager",
    opening="I am writing to express my strong interest in the Senior Software Engineer position at Acme Corp. With five years of experience building scalable web applications and a genuine passion for clean, well-tested code, I am excited about the opportunity to contribute to your engineering team.",
    body_1="In my current role at Tech Co, I led the migration of a monolithic application to a microservices architecture, reducing deployment time by 60% and improving system uptime to 99.9%. I collaborated closely with product and design to ship features serving over 200,000 active users, and mentored two junior engineers through their first production deployments.",
    body_2="I am particularly drawn to Acme Corp's commitment to developer productivity and open-source contributions. My experience with Python, Docker, and AWS aligns directly with your stack, and I thrive in the kind of fast-moving, collaborative environment your team is known for.",
    closing="I would love the opportunity to discuss how my background can help Acme Corp continue to scale. Thank you for your time and consideration — I look forward to hearing from you.",
    template="classic",
)


# ── Service ───────────────────────────────────────────────────────────────────

def _to_ctx(data: CoverLetterData) -> dict:
    return {
        "sender":         data.sender.__dict__,
        "date":           data.date,
        "company":        data.company,
        "job_title":      data.job_title,
        "hiring_manager": data.hiring_manager,
        "opening":        data.opening,
        "body_1":         data.body_1,
        "body_2":         data.body_2,
        "closing":        data.closing,
    }


def render_cover_letter_html(data: CoverLetterData) -> str:
    tpl = TEMPLATES.get(data.template, TEMPLATES["classic"])
    return render_template(tpl, **_to_ctx(data))


def generate_pdf(html: str) -> bytes:
    from weasyprint import HTML
    return HTML(string=html).write_pdf()


def _parse_form(form) -> CoverLetterData:
    return CoverLetterData(
        sender=SenderInfo(
            name=form.get("name", ""),
            email=form.get("email", ""),
            phone=form.get("phone", ""),
            location=form.get("location", ""),
            linkedin=form.get("linkedin", ""),
            website=form.get("website", ""),
        ),
        date=form.get("date", ""),
        company=form.get("company", ""),
        job_title=form.get("job_title", ""),
        hiring_manager=form.get("hiring_manager", ""),
        opening=form.get("opening", ""),
        body_1=form.get("body_1", ""),
        body_2=form.get("body_2", ""),
        closing=form.get("closing", ""),
        template=form.get("template", "classic"),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@cover_letter_bp.get("/")
def index():
    sample_html = render_cover_letter_html(_SAMPLE)
    return render_template(
        "cover_letter_index.html",
        templates=list(TEMPLATES.keys()),
        sample_html=sample_html,
    )


@cover_letter_bp.post("/preview")
def preview():
    try:
        data = _parse_form(request.form)
    except Exception as e:
        return str(e), 422
    return render_cover_letter_html(data)


@cover_letter_bp.post("/download")
def download():
    try:
        data = _parse_form(request.form)
    except Exception as e:
        return str(e), 422
    html = render_cover_letter_html(data)
    pdf_bytes = generate_pdf(html)
    filename = f"{data.sender.name.replace(' ', '_')}_cover_letter.pdf"
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp
