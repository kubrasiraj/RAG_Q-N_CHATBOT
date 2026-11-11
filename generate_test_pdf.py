
from pathlib import Path

import pymupdf


OUTPUT_DIR = Path("test_data")
OUTPUT_FILE = OUTPUT_DIR / "large_test_document_100_pages.pdf"

TOPICS = [
    "Account Registration",
    "Password Security",
    "Order Processing",
    "Delivery Estimates",
    "Shipping Charges",
    "Payment Methods",
    "Refund Eligibility",
    "Return Procedures",
    "Customer Support",
    "Data Privacy",
    "User Permissions",
    "Document Management",
    "System Availability",
    "Service Monitoring",
    "Incident Reporting",
    "Business Continuity",
    "Data Retention",
    "Compliance Requirements",
    "Security Audits",
    "Frequently Asked Questions",
]

FACTS = [
    "Account registration requires a valid email address.",
    "Passwords must never be shared with other users.",
    "Order processing normally takes one to two business days.",
    "Karachi delivery estimates range from two to four business days.",
    "Shipping charges must be checked before payment.",
    "Supported payment methods are displayed at checkout.",
    "Refund eligibility depends on the published refund policy.",
    "Returned products must satisfy the applicable return conditions.",
    "Customers can contact support using their registered account.",
    "Personal information must not be shared with unauthorized users.",
    "User permissions determine which resources an account can access.",
    "Documents must be validated before being stored.",
    "Service availability may be affected by scheduled maintenance.",
    "System monitoring records operational errors and performance.",
    "Security incidents must be reported to the responsible team.",
    "Business continuity procedures describe recovery responsibilities.",
    "Data retention periods depend on the applicable policy.",
    "Compliance requirements must be reviewed periodically.",
    "Security audits evaluate access controls and system weaknesses.",
    "Questions not covered by this document must not be guessed.",
]



def build_page_text(page_number: int) -> str:
    topic_index = (page_number - 1) % len(TOPICS)

    topic = TOPICS[topic_index]
    fact = FACTS[topic_index]

    paragraphs = [
        f"Section {page_number}: {topic}",
        f"Important rule: {fact}",
    ]

    for index in range(1, 9):
        paragraphs.append(
            f"{topic} procedure {index}: "
            f"Users should follow the documented process, "
            f"verify the information before submitting a request, "
            f"and retain the relevant confirmation for future reference. "
            f"Support teams should use the official records rather than "
            f"making assumptions about account activity or service status."
        )

    return "\n\n".join(paragraphs)



def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf = pymupdf.open()

    for page_number in range(1, 101):
        page = pdf.new_page(width=595, height=842)

        text = build_page_text(page_number)

        result = page.insert_textbox(
            pymupdf.Rect(45, 45, 550, 790),
            text,
            fontsize=9,
            fontname="helv",
            lineheight=1.25,
        )

        if result < 0:
            raise RuntimeError(
                f"Text overflow on page {page_number}. "
                "Reduce the content or font size."
            )

    pdf.save(OUTPUT_FILE)
    pdf.close()

    print(f"Created: {OUTPUT_FILE.resolve()}")
    print("Pages: 100")
    print("Database was not modified.")


if __name__ == "__main__":
    main()
