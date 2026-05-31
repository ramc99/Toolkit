from dataclasses import dataclass, field
from flask import Blueprint, render_template, request, make_response

resume_bp = Blueprint("resume", __name__, url_prefix="/resume")

# ── Models ────────────────────────────────────────────────────────────────────

@dataclass
class Skill:
    name: str
    level: int = 3


@dataclass
class ContactInfo:
    name: str
    email: str
    phone: str
    location: str
    linkedin: str = ""
    website: str = ""


@dataclass
class WorkExperience:
    company: str
    role: str
    start_date: str
    end_date: str
    bullets: list


@dataclass
class Education:
    institution: str
    degree: str
    field: str
    start_date: str
    end_date: str
    gpa: str = ""


@dataclass
class Certification:
    name: str
    issuer: str
    issue_date: str
    credential_id: str = ""
    url: str = ""


@dataclass
class Project:
    name: str
    description: str
    url: str = ""
    start_date: str = ""
    end_date: str = ""


@dataclass
class Language:
    name: str
    proficiency: str


@dataclass
class Award:
    title: str
    issuer: str
    date: str
    description: str = ""


@dataclass
class ResumeData:
    contact: ContactInfo
    summary: str
    experience: list
    education: list
    skills: list
    certifications: list = field(default_factory=list)
    projects: list = field(default_factory=list)
    languages: list = field(default_factory=list)
    awards: list = field(default_factory=list)
    template: str = "modern_1"


# ── Template registry ─────────────────────────────────────────────────────────

TEMPLATES = {
    "modern_1": "resumes/modern_1.html",
    "modern_2": "resumes/modern_2.html",
    "modern_3": "resumes/modern_3.html",
    "modern_4": "resumes/modern_4.html",
    "modern_5": "resumes/modern_5.html",
    "modern_6": "resumes/modern_6.html",
}

_SAMPLE = ResumeData(
    contact=ContactInfo(
        name="Your Name",
        email="yourname@email.com",
        phone="+1 555 000 0000",
        location="City, State",
        linkedin="linkedin.com/in/yourname",
        website="yourwebsite.com",
    ),
    summary="A results-driven professional with a track record of delivering high-impact projects. Experienced in building scalable systems and collaborating across teams to ship great products.",
    experience=[
        WorkExperience(
            company="Company Name",
            role="Your Job Title",
            start_date="Jan 2021",
            end_date="Present",
            bullets=[
                "Delivered a key initiative that improved system performance by 40%",
                "Collaborated with product and design to ship 3 major features on schedule",
                "Mentored 2 junior engineers through onboarding and code reviews",
            ],
        ),
        WorkExperience(
            company="Previous Employer",
            role="Previous Role",
            start_date="Jun 2018",
            end_date="Dec 2020",
            bullets=[
                "Built and maintained core product features used by 50,000+ users",
                "Reduced deployment time from 2 hours to 15 minutes via CI/CD improvements",
            ],
        ),
    ],
    education=[
        Education(
            institution="University Name",
            degree="Bachelor of Science",
            field="Your Field of Study",
            start_date="2014",
            end_date="2018",
            gpa="3.8",
        ),
    ],
    skills=[
        Skill("Python", 5),
        Skill("Flask", 4),
        Skill("PostgreSQL", 4),
        Skill("Docker", 3),
        Skill("AWS", 3),
        Skill("Git", 5),
    ],
    certifications=[
        Certification(
            name="AWS Certified Solutions Architect",
            issuer="Amazon Web Services",
            issue_date="Mar 2023",
            credential_id="AWS-SAA-C03",
        ),
    ],
    projects=[
        Project(
            name="PDF Toolkit App",
            description="A full-featured web app for splitting, merging, compressing, and converting PDF documents.",
            url="github.com/yourname/pdf-toolkit",
            start_date="Jan 2024",
            end_date="Present",
        ),
    ],
    languages=[
        Language(name="English", proficiency="Native"),
        Language(name="Spanish", proficiency="Intermediate"),
    ],
    awards=[
        Award(
            title="Employee of the Quarter",
            issuer="Acme Corp",
            date="Q2 2022",
            description="Recognized for outstanding contributions to the platform team.",
        ),
    ],
    template="modern_1",
)


# ── Service ───────────────────────────────────────────────────────────────────

def _to_ctx(data: ResumeData) -> dict:
    return {
        "contact":        data.contact.__dict__,
        "summary":        data.summary,
        "experience":     [e.__dict__ for e in data.experience],
        "education":      [e.__dict__ for e in data.education],
        "skills":         [s.__dict__ for s in data.skills],
        "certifications": [c.__dict__ for c in data.certifications],
        "projects":       [p.__dict__ for p in data.projects],
        "languages":      [l.__dict__ for l in data.languages],
        "awards":         [a.__dict__ for a in data.awards],
    }


def render_resume_html(data: ResumeData) -> str:
    tpl = TEMPLATES.get(data.template, TEMPLATES["modern_1"])
    return render_template(tpl, **_to_ctx(data))


def generate_pdf(html: str) -> bytes:
    from weasyprint import HTML
    return HTML(string=html).write_pdf()


# ── Form parser ───────────────────────────────────────────────────────────────

def _parse_form(form) -> ResumeData:
    companies = form.getlist("company")
    experience = [
        WorkExperience(
            company=companies[i],
            role=form.getlist("role")[i],
            start_date=form.getlist("exp_start")[i],
            end_date=form.getlist("exp_end")[i],
            bullets=[b.strip() for b in form.getlist("bullets")[i].splitlines() if b.strip()],
        )
        for i in range(len(companies))
        if companies[i].strip()
    ]

    institutions = form.getlist("institution")
    gpas = form.getlist("gpa")
    education = [
        Education(
            institution=institutions[i],
            degree=form.getlist("degree")[i],
            field=form.getlist("field")[i],
            start_date=form.getlist("edu_start")[i],
            end_date=form.getlist("edu_end")[i],
            gpa=gpas[i] if i < len(gpas) else "",
        )
        for i in range(len(institutions))
        if institutions[i].strip()
    ]

    skills = [
        Skill(name=n, level=max(1, min(5, int(lvl or 3))))
        for n, lvl in zip(form.getlist("skill_name"), form.getlist("skill_level"))
        if n.strip()
    ]

    cert_names = form.getlist("cert_name")
    cert_issuers = form.getlist("cert_issuer")
    cert_dates = form.getlist("cert_date")
    cert_ids = form.getlist("cert_id")
    cert_urls = form.getlist("cert_url")
    certifications = [
        Certification(
            name=cert_names[i],
            issuer=cert_issuers[i] if i < len(cert_issuers) else "",
            issue_date=cert_dates[i] if i < len(cert_dates) else "",
            credential_id=cert_ids[i] if i < len(cert_ids) else "",
            url=cert_urls[i] if i < len(cert_urls) else "",
        )
        for i in range(len(cert_names))
        if cert_names[i].strip()
    ]

    proj_names = form.getlist("proj_name")
    proj_descs = form.getlist("proj_desc")
    proj_urls = form.getlist("proj_url")
    proj_starts = form.getlist("proj_start")
    proj_ends = form.getlist("proj_end")
    projects = [
        Project(
            name=proj_names[i],
            description=proj_descs[i] if i < len(proj_descs) else "",
            url=proj_urls[i] if i < len(proj_urls) else "",
            start_date=proj_starts[i] if i < len(proj_starts) else "",
            end_date=proj_ends[i] if i < len(proj_ends) else "",
        )
        for i in range(len(proj_names))
        if proj_names[i].strip()
    ]

    lang_names = form.getlist("lang_name")
    lang_profs = form.getlist("lang_prof")
    languages = [
        Language(
            name=lang_names[i],
            proficiency=lang_profs[i] if i < len(lang_profs) else "Fluent",
        )
        for i in range(len(lang_names))
        if lang_names[i].strip()
    ]

    award_titles = form.getlist("award_title")
    award_issuers = form.getlist("award_issuer")
    award_dates = form.getlist("award_date")
    award_descs = form.getlist("award_desc")
    awards = [
        Award(
            title=award_titles[i],
            issuer=award_issuers[i] if i < len(award_issuers) else "",
            date=award_dates[i] if i < len(award_dates) else "",
            description=award_descs[i] if i < len(award_descs) else "",
        )
        for i in range(len(award_titles))
        if award_titles[i].strip()
    ]

    return ResumeData(
        contact=ContactInfo(
            name=form.get("name", ""),
            email=form.get("email", ""),
            phone=form.get("phone", ""),
            location=form.get("location", ""),
            linkedin=form.get("linkedin", ""),
            website=form.get("website", ""),
        ),
        summary=form.get("summary", ""),
        experience=experience,
        education=education,
        skills=skills,
        certifications=certifications,
        projects=projects,
        languages=languages,
        awards=awards,
        template=form.get("template", "modern_1"),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@resume_bp.get("/")
def index():
    sample_html = render_resume_html(_SAMPLE)
    return render_template(
        "resume_index.html",
        templates=list(TEMPLATES.keys()),
        sample_html=sample_html,
    )


@resume_bp.post("/preview")
def preview():
    try:
        data = _parse_form(request.form)
    except Exception as e:
        return str(e), 422
    return render_resume_html(data)


@resume_bp.post("/download")
def download():
    try:
        data = _parse_form(request.form)
    except Exception as e:
        return str(e), 422
    html = render_resume_html(data)
    pdf_bytes = generate_pdf(html)
    filename = f"{data.contact.name.replace(' ', '_')}_resume.pdf"
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp
