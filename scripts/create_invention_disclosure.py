"""Fill the supplied static IDF-B template and append a measured research annex.

Run with the bundled PDF Python runtime. Source PDF is preserved.
"""

import io
import json
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/Users/somyadeeptarat/Downloads/Invention_Disclosure_Format_B.pdf")
OUTPUT = ROOT / "output/pdf/FraudDetectAI_Invention_Disclosure_B_Draft.pdf"
METRICS = json.loads(
    (ROOT / "docs/evaluation/joint_funding_evaluation.json").read_text()
)
NAVY = colors.HexColor("#19364B")
TEAL = colors.HexColor("#087E8B")
GRAY = colors.HexColor("#52616B")
TITLE = "Decision-Directed Ledger Evidence Acquisition Using Joint Funding Bounds"

PRIOR = [
    (
        "P1",
        "FlowScope (AAAI, 2020)",
        "https://cdn.aaai.org/ojs/5906/5906-13-9131-1-10-20200513.pdf",
        "Multi-step flow-based laundering detection.",
        "Flow conservation and multi-account tracing are not new.",
    ),
    (
        "P2",
        "US11854091B1 (2023); priority 2020-07-24",
        "https://patents.google.com/patent/US11854091B1/en",
        "Transaction tracing; FIFO attribution and graph transformations. Claim 1 addresses policy enforcement with distributed mapping.",
        "Our prototype retains all feasible allocations instead of choosing FIFO. Tracing and replay remain overlapping concepts.",
    ),
    (
        "P3",
        "CN112465638A (2021)",
        "https://patents.google.com/patent/CN112465638A/en",
        "Split/combined transaction tracing using graph storage, parameters and search.",
        "Split-and-merge tracking alone is not a novelty claim.",
    ),
    (
        "P4",
        "US20250045762A1 (2025)",
        "https://patents.google.com/patent/US20250045762A1/en",
        "Claim 1 covers temporal graph profiles updated using new transactions.",
        "Generic graph features and temporal updates are established.",
    ),
    (
        "P5",
        "WO2026125967A1 (2026)",
        "https://patents.google.com/patent/WO2026125967A1/en",
        "Claim 1 includes ML-based fraud identification, fund tags, tracing and responsive measures.",
        "Our offline prototype computes intervals and recommends evidence; tracking plus action is already disclosed.",
    ),
    (
        "P6",
        "EDDI (2018 preprint)",
        "https://arxiv.org/abs/1809.11142",
        "Dynamic acquisition of useful missing information using expected information gain.",
        "Selecting the next evidence is not new in general; the proposed policy uses worst-case funding-condition ambiguity.",
    ),
    (
        "P7",
        "CN120852050B (2026); A publication 2025-10-28",
        "https://patents.google.com/patent/CN120852050B/en",
        "Graph fusion, fund-path reconstruction and counterfactual causal-query scenarios.",
        "Counterfactual fund-path analysis is overlapping prior art; our queries concern obtainable boundary evidence.",
    ),
]

TEXT = {
    1: [
        TITLE
        + ". Working title for a research disclosure, not a representation that a patent has been granted or that novelty is established."
    ],
    2: [
        "Computer-implemented financial investigation, transaction-network analysis, constrained optimization, and evidence selection. Intended application: investigation of complaint-linked instant-payment proceeds that split through mule accounts, mix with other funds, and converge at related recipients."
    ],
    4: [
        "A mixed account does not identify which incoming rupees funded an outgoing payment. Independent per-payment intervals can also conceal a collective constraint: two payments may each have zero minimum source attribution although their combined minimum is positive. The existing project implements single-account FABC; this prototype computes joint terminal-account holdings across a chronological network.",
        "The proposed gap is decision-directed evidence acquisition tied to joint feasible funding bounds: when a funding condition is unresolved, choose an obtainable boundary record using its worst-case effect on that condition. Existing work establishes flow tracing, graph detection and active information acquisition separately. The combination remains an inventive-step hypothesis. No claim-level novelty clearance or freedom-to-operate conclusion has been obtained.",
        "Assessment: sufficient motivation for an isolated experimental prototype; insufficient evidence to assert patentability or improved real-world fraud detection. The simple reachability baseline ties the proposed selector in the current microbenchmark. Accordingly, readiness for production implementation or filing-ready novelty claims has not been established.",
    ],
    5: [
        "Compute exact minimum and maximum cohort-attributable funds across a set of final account holdings without double counting serial transfers.",
        "Distinguish a met, unmet or unresolved funding review condition from any fraud verdict; preserve irreducible uncertainty caused by fungibility.",
        "Select a positive-benefit, obtainable evidence query under an explicit acquisition cost and exhaustive response partitions, without inventing response probabilities.",
        "Produce a replayable evidence-bound certificate and independently check endpoint feasibility and optimality. Measure correctness and query behavior before introducing a production workflow.",
    ],
    6: [
        "Build an account-event network from a complete ordered ledger. Capacity-constrained edges represent transfers and retained balances. Boundary intervals describe independently supported source-cohort amounts. Solve two integer min-cost circulations to find the smallest and largest total cohort amount in selected final accounts.",
        "If the interval straddles the review threshold, simulate every supplied outcome of each obtainable boundary-evidence query. Rank queries by guaranteed reduction in unresolved interval width per unit cost. Apply an authenticated response as a constraint update, fully recompute the certificate, and keep the response reference. The prototype simulates acquisition; it does not contact banks.",
    ],
    7: [
        "Inputs: snapshot identifier, cohort identifier, one currency, opening balances with cohort bounds, an ordered list of internal transfers or external credits, distinct target accounts, a positive review threshold, and optional query specifications. Values are integer minor units. No overdrafts, external withdrawals, fees, FX or incomplete ledgers are supported. A complete=true declaration is a caller assertion, not independently authenticated bank evidence.",
        "Network: each balance event receives a new node. A transfer edge has the posted transfer capacity; a carry edge has the balance retained after the event. Opening funds and external credits enter through boundary edges with lower/upper cohort amounts. Every final account drains to a common sink; a return edge closes the circulation. Only selected final-account sink edges enter the objective. This terminal frontier prevents serial double counting.",
        "Let F be all integer flows satisfying edge bounds and conservation, and T be target terminal edges. Compute L = min over z in F of sum(z_e for e in T), and U = max over z in F of the same sum. The implementation uses NetworkX network_simplex with lower-bound demand transformation and opposite objective signs. These are established optimization techniques, not claimed inventions.",
        "For threshold tau: MET if L >= tau; NOT_MET if U < tau; otherwise UNRESOLVED. These refer exclusively to source funding. Complaint-linked sources can be mistaken, legitimate merchants can pass funds through, and exact attribution cannot prove deceptive intent.",
        "Define D([L,U]) = U-L for an unresolved condition and zero otherwise. A query q has positive integer cost c_q and outcomes that partition the entire current boundary interval with no gaps or overlaps. Score(q) = (D(current) - max over outcomes o of D(after q=o)) / c_q. Choose the greatest positive score; break ties by cost then identifier. A null selection means no useful one-step query, not that all possible combinations of queries are useless.",
        "Queries may constrain only an externally attestable boundary amount, such as an authoritative upstream certificate. They may not pretend to reveal an arbitrary allocation inside a mixed account. Outcome partition completeness is validated. Costs and the existence of a usable evidence source are supplied assumptions; production authentication and permissions are not implemented.",
        "Certificate: save input evidence, cohort/snapshot identity, threshold, version, both endpoint assignments, solver version and canonical SHA-256 digest. Verify integer capacities, conservation, objective totals and absence of a negative residual cycle for each endpoint objective. The residual check certifies optimality without rerunning network_simplex. Hashes do not establish source truth or resist an administrator who rewrites evidence and recomputes the digest.",
        "Implementation boundary: app/services/joint_funding.py provides analyze, verify, rank_evidence and apply_evidence. The CLI is scripts/run_joint_funding.py. This is an offline prototype; live transfers, alert thresholds and the database schema are unchanged. Incremental optimization, learned query probabilities, bank connectors, automated holds and a trained fraud classifier using the new features are not implemented.",
    ],
    8: [
        "Correctness: 250 seeded small ledgers (seeds 0-249) were checked against independent exhaustive enumeration of all feasible integer allocations. All 250 matched exactly. The new test module passed 272 tests. The complete repository suite passed 394 tests with one skip; PostgreSQL-specific behavior was not established by this run. These counts are software validation, not fraud-detection accuracy.",
        "Split/merge example: INR 10,000 of other opening funds plus INR 10,000 of cohort funds is split into two INR 10,000 payments. Each recipient separately has [0, 10,000] cohort holdings. Together they have [10,000, 10,000]. After both forward everything to a zero-balance recipient, that recipient also has [10,000, 10,000].",
        "Evidence-selection experiment: 100 constructed cases, one useful source-boundary query and one disconnected higher-width distractor, equal cost and a one-query budget. The proposed selector resolved the funding condition for every outcome in 100/100 cases; widest-boundary selection did so in 0/100; seeded random selection in 40/100 (uniform-random expectation: 50/100). A reachability filter followed by widest-boundary selection also achieved 100/100. This intentionally narrow experiment establishes behavior, not superiority over a strong baseline.",
        "Measured local timing includes certificate verification and counterfactual solves where applicable. Hardware architecture: arm64; Python "
        + METRICS["runtime"]["python"]
        + "; NetworkX "
        + METRICS["runtime"]["networkx"]
        + ". Small-ledger analysis p50/p95: "
        + str(METRICS["oracle"]["analyze_including_certificate_verification"]["p50_ms"])
        + "/"
        + str(METRICS["oracle"]["analyze_including_certificate_verification"]["p95_ms"])
        + " ms. Two-query selection p50/p95: "
        + str(
            METRICS["query_microbenchmark"][
                "selection_including_counterfactual_solves"
            ]["p50_ms"]
        )
        + "/"
        + str(
            METRICS["query_microbenchmark"][
                "selection_including_counterfactual_solves"
            ]["p95_ms"]
        )
        + " ms. These tiny synthetic workloads exclude real data retrieval and are not production latency estimates.",
        "Negative and integrity checks cover overdrafts, incomplete inputs, duplicate targets/evidence, floating monetary values, invalid query partitions, attempts to query internal allocations, digest tampering and feasible-but-nonoptimal endpoint substitution. Large integer amounts remain exact. Irreducible fungibility can correctly produce no recommended query.",
        "Not measured: fraud precision/recall, false alerts on real merchants, actual investigator effort, real retrieval savings, incremental speedup, or legal novelty. No customer dataset was used. Results and example inputs are saved under docs/evaluation/joint_funding_*.json; reproduction commands appear below.",
    ],
    9: [
        "Candidate aspect for professional assessment: the operational sequence of computing jointly feasible terminal-funding intervals, detecting review-boundary ambiguity, evaluating exhaustive outcomes of obtainable boundary-evidence queries, selecting by worst-case decision benefit per cost, and issuing a verified updated certificate.",
        "Potential narrower implementation detail: explicit separation of factual boundary uncertainty from unobservable internal allocation choices, combined with refusal to acquire evidence when no positive one-step benefit is certified. This is a candidate claim focus, not a conclusion that the distinction is new or non-obvious.",
        "Do not claim exclusive novelty in network flows, min-cost circulation, integer arithmetic, negative-cycle optimality checks, hashing, generic active acquisition, graph fraud detection, FIFO alternatives, or split/merge tracing. Adding these known parts is not itself evidence of an inventive step.",
        "Gate status: technical proof of concept PASS within stated assumptions; all ten disclosure topics ANSWERED; improvement over strong baselines NOT DEMONSTRATED; novelty/inventive step UNRESOLVED; jurisdictional eligibility and freedom to operate NOT ASSESSED. No patent application has been filed or submitted through this work.",
        "Before filing: obtain a professional claim chart across cited families and citations, search robust attribution/network tomography/active diagnosis/database provenance beyond fraud terminology, test against stronger query policies on withheld realistic cases, and document an actual technical effect. If filing in India, review the official patent requirements and current CRI guidelines [L1-L2]. Human inventorship, ownership and disclosure history require the actual contributors' records; they are not inferred from this draft.",
    ],
    10: [
        "TRL 3 - experimental proof of concept (provisional self-assessment). Executable algorithms, synthetic demonstrations, oracle checks and test evidence exist. No integrated bank pilot, relevant operational environment, production qualification or real-customer performance validation has occurred. TRL 4-9 would overstate the current evidence."
    ],
}

HEADINGS = {
    1: "Title of the invention",
    2: "Field / area of invention",
    3: "Prior patents and publications from literature",
    4: "Summary and background: gap and novelty",
    5: "Objectives of invention",
    6: "Working principle in brief",
    7: "Detailed description and drawing",
    8: "Experimental validation results",
    9: "Aspects proposed for protection",
    10: "Technology readiness level",
}

COMMANDS = [
    ".venv/bin/python -m pytest tests/test_joint_funding.py -q",
    ".venv/bin/python -m scripts.evaluate_joint_funding",
    ".venv/bin/python -m scripts.run_joint_funding docs/evaluation/joint_funding_example.json docs/evaluation/joint_funding_certificate.json",
]


class Workflow(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = 487, 145

    def draw(self):
        c = self.canv
        boxes = [
            (0, 82, "Ordered ledger", "Boundary evidence"),
            (169, 82, "Joint bounds", "Two exact optimizations"),
            (338, 82, "Review condition", "MET / NOT_MET / unresolved"),
            (338, 12, "Evidence selection", "Worst-case benefit / cost"),
            (169, 12, "Response update", "Obtain and authenticate*"),
            (0, 12, "Verified certificate", "Replay and optimality check"),
        ]
        for x, y, title, sub in boxes:
            c.setFillColor(colors.HexColor("#ECF4F6"))
            c.setStrokeColor(TEAL)
            c.roundRect(x, y, 149, 48, 5, fill=1)
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(x + 74.5, y + 29, title)
            c.setFont("Helvetica", 7.2)
            c.drawCentredString(x + 74.5, y + 14, sub)
        for x1, y1, x2, y2 in [
            (149, 106, 169, 106),
            (318, 106, 338, 106),
            (412, 82, 412, 60),
            (338, 36, 318, 36),
            (169, 36, 149, 36),
        ]:
            c.setStrokeColor(NAVY)
            c.line(x1, y1, x2, y2)
            if y1 == y2:
                dx = 4 if x2 < x1 else -4
                c.line(x2, y2, x2 + dx, y2 + 3)
                c.line(x2, y2, x2 + dx, y2 - 3)
            else:
                c.line(x2, y2, x2 - 3, y2 + 4)
                c.line(x2, y2, x2 + 3, y2 + 4)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7)
        c.drawString(
            0,
            0,
            "*The prototype simulates evidence responses; it does not authenticate or acquire bank records.",
        )


def create_markdown():
    chunks = [
        "# Invention Disclosure Format B - research draft\n",
        "18 October 2026. Answers mapped to all ten questions. Patent novelty remains unresolved.\n",
    ]
    for number in range(1, 11):
        chunks.append(f"## {number}. {HEADINGS[number]}\n")
        if number == 3:
            chunks.append(
                "| Prior art | Overlap | Difference / limitation |\n| --- | --- | --- |"
            )
            for ref, title, url, overlap, difference in PRIOR:
                chunks.append(f"| [{ref}: {title}]({url}) | {overlap} | {difference} |")
            chunks.append(
                "\nPreliminary public-source review on 18 October 2026. Publication identifiers are not legal-status opinions. No exhaustive family or prosecution review.\n"
            )
        else:
            chunks.extend(p + "\n" for p in TEXT[number])
    chunks.append(
        "## Reproduce the validation\n\n```bash\n" + "\n".join(COMMANDS) + "\n```\n"
    )
    chunks.append(
        "[L1: IP India patent basics](https://ipindia.gov.in/basics-of-patents)\n\n[L2: Official CRI guidelines catalog](https://ipindia.gov.in/resource/patents-resources-guidelines)\n"
    )
    (ROOT / "docs/INVENTION_DISCLOSURE_B_DRAFT.md").write_text("\n".join(chunks))


def main():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "BodyTextCustom",
            fontName="Helvetica",
            fontSize=9.2,
            leading=13,
            textColor=NAVY,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            "SmallCustom",
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=NAVY,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            "HeadingCustom",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=TEAL,
            spaceBefore=10,
            spaceAfter=8,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            "TableCustom",
            fontName="Helvetica",
            fontSize=7.6,
            leading=10,
            textColor=NAVY,
        )
    )

    def p(text, style="BodyTextCustom"):
        return Paragraph(escape(text), styles[style])

    annex = io.BytesIO()
    doc = SimpleDocTemplate(
        annex,
        pagesize=(595.32, 841.92),
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=50,
    )
    story = []
    for number in range(1, 11):
        if number in (4, 7, 8, 9):
            story.append(PageBreak())
        story.append(p(f"{number}. {HEADINGS[number]}", "HeadingCustom"))
        if number == 3:
            rows = [
                [
                    p(x, "TableCustom")
                    for x in (
                        "Prior art",
                        "Established overlap",
                        "Candidate distinction / limit",
                    )
                ]
            ]
            for ref, title, url, overlap, difference in PRIOR:
                linked = Paragraph(
                    f'<link href="{url}" color="#087E8B">{escape(ref + ": " + title)}</link>',
                    styles["TableCustom"],
                )
                rows.append(
                    [linked, p(overlap, "TableCustom"), p(difference, "TableCustom")]
                )
            table = Table(rows, colWidths=[127, 161, 199], repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4EDF1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C2D0D7")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                )
            )
            story.extend(
                [
                    table,
                    Spacer(1, 10),
                    p(
                        "Preliminary public-source review, 18 October 2026. Titles link to source documents. Patent identifiers do not establish current legal status. Family, prosecution and freedom-to-operate review remain outstanding.",
                        "SmallCustom",
                    ),
                ]
            )
        else:
            if number == 7:
                story.extend([Workflow(), Spacer(1, 12)])
            story.extend(p(text) for text in TEXT[number])
    story.append(p("Reproduction and supporting records", "HeadingCustom"))
    story.append(
        p(
            "Run from the repository root. No bank connection or model retraining is required.",
            "SmallCustom",
        )
    )
    for cmd in COMMANDS:
        story.append(p(cmd, "SmallCustom"))
    story.append(
        p(
            "Saved measurements: docs/evaluation/joint_funding_evaluation.json. Example input and certificate: docs/evaluation/joint_funding_example.json and joint_funding_certificate.json.",
            "SmallCustom",
        )
    )
    for title, url in [
        ("L1: IP India - patent basics", "https://ipindia.gov.in/basics-of-patents"),
        (
            "L2: IP India - current CRI guidelines catalog",
            "https://ipindia.gov.in/resource/patents-resources-guidelines",
        ),
    ]:
        story.append(
            Paragraph(
                f'<link href="{url}" color="#087E8B">{title}</link>',
                styles["SmallCustom"],
            )
        )

    def page_header(c, d):
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(54, 811, "FRAUDDETECTAI / IDF-B TECHNICAL ANNEX")
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(
            54,
            796,
            "Research draft | 18 October 2026 | Novelty and patentability unresolved",
        )
        c.drawString(
            54,
            30,
            "Experimental proof of concept - not a fraud verdict or patentability opinion",
        )
        c.drawRightString(541, 30, f"Annex {d.page}")

    doc.build(story, onFirstPage=page_header, onLaterPages=page_header)

    # The source has no AcroForm fields. Add answers as a static overlay without
    # altering the original; the editable answer text is saved separately.
    overlay = io.BytesIO()
    c = canvas.Canvas(overlay, pagesize=(595.32, 841.92))
    field_style = ParagraphStyle(
        "Field", fontName="Helvetica", fontSize=8.5, leading=10.5, textColor=NAVY
    )

    def field(top, bottom, text, width=487):
        paragraph = Paragraph(escape(text), field_style)
        _, height = paragraph.wrap(width, bottom - top)
        if height > bottom - top:
            raise ValueError(f"Template field overflows: {text[:40]}")
        paragraph.drawOn(c, 54, 841.92 - top - height)

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(TEAL)
    c.drawString(
        54, 703, "RESEARCH DRAFT - NOVELTY NOT YET CLEARED - TECHNICAL ANNEX ATTACHED"
    )
    field(180, 207, TITLE)
    field(
        232,
        268,
        "Financial investigation; chronological transaction graphs; constrained funding attribution; decision-directed evidence selection. Use case: scam-proceeds and mule-network investigation.",
    )
    field(
        297,
        360,
        "Prior-art comparison table: annex section 3 (P1-P7). Includes FlowScope; US11854091B1; CN112465638A; US20250045762A1; WO2026125967A1; EDDI; CN120852050B. Generic tracing, graphs and active acquisition are established. The precise combination remains unverified.",
    )
    field(
        389,
        436,
        "Compute joint source-funding intervals and select boundary evidence that can resolve an uncertain review condition. Avoid attributing fungible money to one invented path. Candidate novelty only; stronger-baseline benefit and inventive step remain unproven. See annex section 4.",
    )
    field(
        462,
        510,
        "Exact joint bounds without serial double counting; explicit uncertainty; useful evidence requests under cost; replayable and optimality-checked results. No automatic fraud verdict. See annex section 5.",
    )
    field(
        538,
        586,
        "Build a chronological capacity network; solve minimum/maximum cohort funding; test the review threshold; simulate exhaustive evidence outcomes; rank worst-case decision benefit per cost; update and verify. See annex section 6.",
    )
    field(
        615,
        667,
        "Implemented offline integer-flow solver, terminal-account targets, boundary-evidence query ranking, response application and certificate verification. Architecture drawing, formulas, assumptions and code mapping are in annex section 7. Live payment decisions are unchanged.",
    )
    field(
        696,
        740,
        "250/250 exhaustive-oracle matches; 272 new tests passed; full suite 394 passed, 1 skipped. Query experiment: proposed 100/100, reachability baseline 100/100, widest 0/100, seeded random 40/100. Synthetic results only; see annex section 8.",
    )
    field(
        768,
        818,
        "Candidate: the combined joint-bounds / decision-directed boundary-query / verified-update sequence. Known constituent algorithms are not claimed as new. Patentability and inventive step remain unresolved; professional claim review is required. See annex section 9.",
    )
    c.showPage()
    c.setStrokeColor(TEAL)
    c.setLineWidth(2)
    # Tick the source template's TRL 3 cell (x 156.5-216.2; top 377.1-414.7).
    c.line(177, 446, 184, 439)
    c.line(184, 439, 198, 457)
    field(
        470,
        520,
        "TRL 3 selected: experimental proof of concept. Executable offline algorithm and synthetic validation exist; no bank pilot, operational integration or real-customer validation. This is a provisional self-assessment. See annex section 10.",
    )
    field(
        535,
        610,
        "Readiness decision: research prototype implemented; patent novelty gate remains unresolved. The attached answers are suitable for technical discussion with the institution's IP cell, not a claim that filing requirements are satisfied. Inventorship, ownership and disclosure history must be confirmed by the actual contributors.",
    )
    c.save()
    source, answers = PdfReader(SOURCE), PdfReader(overlay)
    writer = PdfWriter()
    for original, filled in zip(source.pages, answers.pages):
        original.merge_page(filled)
        writer.add_page(original)
    for page in PdfReader(annex).pages:
        writer.add_page(page)
    writer.add_metadata(
        {
            "/Title": TITLE + " - IDF-B Research Draft",
            "/Subject": "Proof of concept; patentability unresolved",
        }
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("wb") as stream:
        writer.write(stream)
    create_markdown()
    check = PdfReader(OUTPUT)
    text = "\n".join(page.extract_text() for page in check.pages)
    assert all(heading in text for heading in HEADINGS.values())
    assert "TRL 3" in text and "250/250" in text
    print(f"Created {OUTPUT} ({len(check.pages)} pages); all ten sections found.")


if __name__ == "__main__":
    main()
