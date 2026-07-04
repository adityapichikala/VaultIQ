"""
Synthetic PDF generator for VaultIQ.
Generates text-based PDF documents simulating internal company documents.
Run: python data/synthetic/generate_pdfs.py
"""

import os
import sys

# We'll use fpdf2 for PDF generation
try:
    from fpdf import FPDF
except ImportError:
    print("Installing fpdf2...")
    os.system(f"{sys.executable} -m pip install fpdf2")
    from fpdf import FPDF


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "pdfs")


class BigCorpPDF(FPDF):
    """Custom PDF class with BigCorp branding."""

    def normalize_text(self, text):
        """Override to handle unicode characters before encoding."""
        text = (
            text.replace("\u2014", "--")
            .replace("\u2013", "-")
            .replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2026", "...")
            .replace("\u2022", "-")
            .replace("\u20b9", "Rs.")
            .replace("\u2264", "<=")
            .replace("\u2265", ">=")
            .replace("\u2248", "~=")
        )
        return super().normalize_text(text)

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "BigCorp Internal -- Confidential", align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def chapter_title(self, title: str):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(33, 37, 41)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(33, 37, 41)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(33, 37, 41)
        self.multi_cell(0, 6, text)
        self.ln(3)

    def bullet_point(self, text: str):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(33, 37, 41)
        indent = 12
        available_w = self.w - self.l_margin - self.r_margin - indent
        x = self.l_margin + indent
        self.set_x(x)
        self.multi_cell(available_w, 6, "- " + text)

    def add_table(self, headers: list, rows: list):
        """Add a simple table."""
        col_width = (self.w - 20) / len(headers)
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(240, 240, 240)
        for h in headers:
            self.cell(col_width, 8, str(h), border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 10)
        for row in rows:
            for item in row:
                self.cell(col_width, 7, str(item), border=1)
            self.ln()
        self.ln(5)


def generate_employee_handbook():
    """Generate a multi-page employee handbook PDF."""
    pdf = BigCorpPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Page 1: Title
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 28)
    pdf.cell(0, 15, "BigCorp Employee Handbook", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Version 5.0 — Effective January 2026", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "Human Resources Department", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "ACL: all-employees", align="C", new_x="LMARGIN", new_y="NEXT")

    # Page 2: Code of Conduct
    pdf.add_page()
    pdf.chapter_title("1. Code of Conduct")
    pdf.body_text(
        "At BigCorp, we believe that a strong ethical foundation is essential for long-term success. "
        "Every employee is expected to act with integrity, respect, and professionalism in all "
        "interactions — with colleagues, customers, partners, and the public."
    )
    pdf.section_title("1.1 Core Values")
    pdf.bullet_point("Integrity: We do the right thing, even when no one is watching")
    pdf.bullet_point("Innovation: We challenge the status quo and embrace creative solutions")
    pdf.bullet_point("Collaboration: We work together across teams and functions")
    pdf.bullet_point("Customer First: Every decision considers the customer impact")
    pdf.bullet_point("Ownership: We take responsibility for our actions and outcomes")

    pdf.section_title("1.2 Workplace Behavior")
    pdf.body_text(
        "BigCorp has zero tolerance for harassment, discrimination, or bullying of any kind. "
        "This includes but is not limited to: unwelcome comments about someone's race, gender, "
        "religion, sexual orientation, disability, or age. Any form of retaliation against someone "
        "who reports a concern is also strictly prohibited."
    )
    pdf.body_text(
        "If you witness or experience inappropriate behavior, report it immediately to your HR "
        "Business Partner or use the anonymous Ethics Hotline at 1800-XXX-XXXX. All reports are "
        "investigated confidentially within 5 business days."
    )

    pdf.section_title("1.3 Conflict of Interest")
    pdf.body_text(
        "Employees must disclose any situation where personal interests could conflict with "
        "BigCorp's interests. This includes: outside employment, financial interests in competitors "
        "or suppliers, and family relationships with other BigCorp employees in reporting lines. "
        "Disclosures are made via the COI form on the HR portal."
    )

    # Page 3: Compensation
    pdf.add_page()
    pdf.chapter_title("2. Compensation & Benefits")
    pdf.section_title("2.1 Salary Structure")
    pdf.body_text(
        "BigCorp follows a transparent compensation philosophy. Salaries are benchmarked annually "
        "against industry data from Aon, Mercer, and Radford surveys. We target the 65th percentile "
        "for base salary and 75th percentile for total compensation (base + bonus + equity)."
    )

    pdf.add_table(
        ["Component", "Frequency", "Eligibility"],
        [
            ["Base Salary", "Monthly", "All employees"],
            ["Performance Bonus", "Annual (March)", "L2+ with 1yr tenure"],
            ["Stock Options (ESOP)", "Annual vesting", "L3+ (4-year vest, 1yr cliff)"],
            ["Spot Bonus", "Ad-hoc", "Any employee, manager-nominated"],
            ["Retention Bonus", "One-time", "Critical talent, VP-approved"],
        ],
    )

    pdf.section_title("2.2 Benefits Summary")
    pdf.body_text(
        "All full-time employees are eligible for the following benefits from Day 1:"
    )
    pdf.bullet_point("Health insurance: Rs. 10 Lakh cover (self + spouse + 2 children + parents)")
    pdf.bullet_point("Term life insurance: 3x annual CTC")
    pdf.bullet_point("Dental and vision: Included in health insurance")
    pdf.bullet_point("Mental health: 8 free counseling sessions/year via Manah Wellness")
    pdf.bullet_point("Gym/fitness: Rs. 5,000/quarter reimbursement")
    pdf.bullet_point("Learning budget: Rs. 50,000/year for courses, conferences, books")
    pdf.bullet_point("Meal allowance: Rs. 2,500/month (tax-exempt)")
    pdf.bullet_point("Internet reimbursement: Rs. 1,500/month for remote workers")

    # Page 4: Performance Reviews
    pdf.add_page()
    pdf.chapter_title("3. Performance Management")
    pdf.section_title("3.1 Review Cycle")
    pdf.body_text(
        "BigCorp runs a semi-annual performance review cycle:"
    )
    pdf.add_table(
        ["Phase", "Timeline", "What Happens"],
        [
            ["Goal Setting", "January / July", "Set 3-5 OKRs with manager"],
            ["Mid-Cycle Check", "March / September", "Progress review, course-correct"],
            ["Self-Assessment", "May / November", "Employee writes self-review"],
            ["Manager Review", "June / December", "Manager rates + writes feedback"],
            ["Calibration", "June / December", "Skip-level alignment on ratings"],
            ["Feedback Delivery", "July / January", "1:1 with manager, rating shared"],
        ],
    )

    pdf.section_title("3.2 Rating Scale")
    pdf.add_table(
        ["Rating", "Label", "Typical % of Employees"],
        [
            ["5", "Exceptional", "5-10%"],
            ["4", "Exceeds Expectations", "20-25%"],
            ["3", "Meets Expectations", "50-60%"],
            ["2", "Needs Improvement", "10-15%"],
            ["1", "Unsatisfactory", "0-5%"],
        ],
    )

    pdf.body_text(
        "A rating of 2 for two consecutive cycles triggers a Performance Improvement Plan (PIP). "
        "A rating of 1 triggers an immediate PIP. PIPs are 60-90 days and include specific, "
        "measurable goals with weekly check-ins."
    )

    pdf.section_title("3.3 Promotions")
    pdf.body_text(
        "Promotions are considered during the June and December calibration cycles. "
        "Requirements: minimum 18 months at current level, rating of 4+ in last cycle, "
        "and a written promotion packet reviewed by skip-level manager. "
        "Promotion packets include: impact summary, peer feedback, scope expansion evidence."
    )

    pdf.output(os.path.join(OUTPUT_DIR, "employee_handbook.pdf"))
    print("  Generated: employee_handbook.pdf (4 pages)")


def generate_quarterly_report():
    """Generate a Q1 2026 financial summary PDF."""
    pdf = BigCorpPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.add_page()
    pdf.chapter_title("Q1 2026 Financial Summary")
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "Prepared by: Finance Team | ACL: leadership", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.section_title("Revenue Overview")
    pdf.body_text(
        "Total revenue for Q1 2026 was Rs. 142 Crore, representing a 23% year-over-year growth "
        "and 8% quarter-over-quarter growth. This exceeded the target of Rs. 135 Crore by 5.2%. "
        "Key growth drivers were the Marketplace segment (+31% YoY) and the new Enterprise "
        "tier which contributed Rs. 12 Crore in its first full quarter."
    )

    pdf.add_table(
        ["Segment", "Revenue (Cr)", "YoY Growth", "Target"],
        [
            ["Marketplace", "82", "+31%", "75"],
            ["Payments (MDR)", "35", "+18%", "38"],
            ["Enterprise", "12", "New", "10"],
            ["Other", "13", "+5%", "12"],
            ["TOTAL", "142", "+23%", "135"],
        ],
    )

    pdf.section_title("Key Metrics")
    pdf.add_table(
        ["Metric", "Q1 2026", "Q4 2025", "Change"],
        [
            ["GMV", "Rs. 2,840 Cr", "Rs. 2,630 Cr", "+8%"],
            ["Active Users (MAU)", "8.2M", "7.5M", "+9.3%"],
            ["Orders/Day", "185K", "168K", "+10.1%"],
            ["Take Rate", "5.0%", "4.9%", "+0.1pp"],
            ["ARPU", "Rs. 1,732", "Rs. 1,658", "+4.5%"],
        ],
    )

    pdf.section_title("Cost Structure")
    pdf.body_text(
        "Total operating costs were Rs. 128 Crore, resulting in an operating margin of 9.9%. "
        "Cloud infrastructure costs increased by 15% due to GenAI workloads. "
        "Employee costs were 2% under budget due to slower-than-planned hiring. "
        "The LLM API cost line item (Rs. 24 Lakh in Q1) is a new cost center that "
        "needs closer monitoring as we scale the GenAI product."
    )

    pdf.section_title("Cash Position")
    pdf.body_text(
        "Cash and equivalents: Rs. 284 Crore. Runway at current burn rate: 22 months. "
        "The board has approved raising a Series C of $30-40M in Q3 2026 to fund "
        "international expansion and the enterprise product. Goldman Sachs has been "
        "engaged as the investment banker."
    )

    pdf.output(os.path.join(OUTPUT_DIR, "q1_2026_financial_summary.pdf"))
    print("  Generated: q1_2026_financial_summary.pdf (1 page)")


def generate_architecture_doc():
    """Generate a system architecture overview PDF."""
    pdf = BigCorpPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.add_page()
    pdf.chapter_title("BigCorp Platform Architecture Overview")
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "Author: Arjun Nair (Platform Engineering) | ACL: engineering", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "Version: 3.1 | Last Updated: April 2026", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.section_title("System Overview")
    pdf.body_text(
        "BigCorp's platform is built on a microservices architecture running on AWS EKS "
        "(Kubernetes). We operate 28 production services across 3 AWS regions "
        "(ap-south-1, us-east-1, eu-west-1). Traffic is routed via Cloudflare CDN "
        "and AWS ALB. Service-to-service communication uses gRPC internally and "
        "REST externally."
    )

    pdf.section_title("Core Services")
    pdf.add_table(
        ["Service", "Language", "Database", "Owner"],
        [
            ["user-service", "Go", "PostgreSQL", "User Platform"],
            ["auth-service", "Go", "Redis + Postgres", "User Platform"],
            ["payment-service", "Java", "PostgreSQL", "Payments"],
            ["order-service", "Python", "PostgreSQL", "Marketplace"],
            ["catalog-service", "Python", "MongoDB + ES", "Marketplace"],
            ["search-service", "Python", "Elasticsearch", "Marketplace"],
            ["notification-svc", "Node.js", "Redis", "User Platform"],
            ["ml-serving", "Python", "Redis (cache)", "ML Platform"],
            ["analytics-ingester", "Go", "Kafka + S3", "Data Platform"],
        ],
    )

    pdf.section_title("Data Infrastructure")
    pdf.body_text(
        "Our data stack follows a medallion architecture (bronze-silver-gold):\n"
        "- Bronze: Raw events land in S3 via Kafka Connect (Confluent Cloud)\n"
        "- Silver: Spark jobs (EMR Serverless) clean and deduplicate\n"
        "- Gold: dbt models in Snowflake serve analytics and ML\n"
        "- Feature Store: Feast on Redis (online) + S3/Parquet (offline)\n"
        "- Orchestration: Airflow on EKS (managed via Helm)"
    )

    pdf.section_title("Observability Stack")
    pdf.add_table(
        ["Layer", "Tool", "Retention"],
        [
            ["Metrics", "DataDog", "15 months"],
            ["Logs", "DataDog Logs", "30 days hot, 1yr cold"],
            ["Traces", "DataDog APM", "15 days"],
            ["Alerts", "PagerDuty", "N/A"],
            ["Uptime", "DataDog Synthetics", "N/A"],
            ["Error Tracking", "Sentry", "90 days"],
        ],
    )

    pdf.section_title("Security Architecture")
    pdf.body_text(
        "Authentication: OAuth 2.0 via Auth0 (customer-facing) and Okta (internal SSO). "
        "Secrets management: AWS Secrets Manager + Sealed Secrets for K8s. "
        "Network: VPC with private subnets, NAT gateway, no public IPs on services. "
        "WAF: Cloudflare WAF (OWASP Top 10 rules) + AWS WAF on ALB. "
        "Encryption: TLS 1.3 in transit, AES-256 at rest (KMS-managed keys). "
        "Access control: IAM roles with least-privilege, reviewed quarterly."
    )

    pdf.output(os.path.join(OUTPUT_DIR, "platform_architecture_overview.pdf"))
    print("  Generated: platform_architecture_overview.pdf (2 pages)")


def generate_security_policy():
    """Generate an information security policy PDF."""
    pdf = BigCorpPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.add_page()
    pdf.chapter_title("Information Security Policy")
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "Owner: CISO Office | ACL: all-employees | Version: 6.0", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.section_title("1. Password Policy")
    pdf.body_text(
        "All employees must adhere to the following password requirements:\n"
        "- Minimum 12 characters\n"
        "- Must contain: uppercase, lowercase, number, and special character\n"
        "- Cannot reuse last 10 passwords\n"
        "- Must be changed every 90 days\n"
        "- Multi-factor authentication (MFA) is mandatory for all systems\n"
        "- Use a password manager (1Password is company-provided)"
    )

    pdf.section_title("2. Device Security")
    pdf.body_text(
        "Company-issued devices:\n"
        "- Full-disk encryption must be enabled (FileVault on Mac, BitLocker on Windows)\n"
        "- Automatic OS updates must be enabled\n"
        "- Company MDM (Jamf/Intune) must be installed\n"
        "- Screen lock after 5 minutes of inactivity\n"
        "- No jailbroken or rooted devices\n"
        "- Personal devices may access email only via the Outlook app with Intune protection"
    )

    pdf.section_title("3. Data Classification & Handling")
    pdf.add_table(
        ["Classification", "Examples", "Sharing Rules"],
        [
            ["Public", "Marketing, blog posts", "Anyone"],
            ["Internal", "Org charts, policies", "Employees only"],
            ["Confidential", "Financial, salary data", "Need-to-know, encrypted"],
            ["Restricted", "PII, health data, keys", "Named access, encrypted, audited"],
        ],
    )

    pdf.section_title("4. Incident Reporting")
    pdf.body_text(
        "All security incidents must be reported within 1 hour of discovery. "
        "Report to: security@bigcorp.internal or call the 24/7 security hotline. "
        "Examples of reportable incidents: phishing emails (forward to phishing@bigcorp.internal), "
        "lost/stolen devices, unauthorized access attempts, suspicious login alerts, "
        "data sent to wrong recipient."
    )

    pdf.section_title("5. Acceptable Use")
    pdf.body_text(
        "Company systems and internet access are for business use. Limited personal use is "
        "acceptable but must not: consume excessive bandwidth, expose the company to legal risk, "
        "or involve accessing inappropriate content. All internet traffic is logged. "
        "Torrenting, cryptocurrency mining, and accessing competitor systems without "
        "authorization are strictly prohibited."
    )

    pdf.output(os.path.join(OUTPUT_DIR, "information_security_policy.pdf"))
    print("  Generated: information_security_policy.pdf (2 pages)")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Generating synthetic PDF documents...")
    generate_employee_handbook()
    generate_quarterly_report()
    generate_architecture_doc()
    generate_security_policy()
    print(f"\nDone! {len(os.listdir(OUTPUT_DIR))} PDFs generated in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
