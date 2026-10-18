"""Rebuild the academic proposal and shared vector diagrams (documentation only)."""
from pathlib import Path
import html
import json
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Polygon
from reportlab.graphics import renderPDF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf'
ASSETS = ROOT / 'docs/diagrams'
OUT.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)
NAVY = '#142C46'
TEAL = '#087F8C'
INK = '#23364D'
MUTED = '#56677A'
PALE = '#EDF4F8'
AMBER = '#A86710'
FONT_ROOT = Path('/Users/somyadeeptarat/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/fonts')
if FONT_ROOT.exists():
    # Embed fonts so diagrams and text render consistently across PDF viewers.
    pdfmetrics.registerFont(TTFont('Helvetica', str(FONT_ROOT / 'Ubuntu-R.ttf')))
    pdfmetrics.registerFont(TTFont('Helvetica-Bold', str(FONT_ROOT / 'Ubuntu-B.ttf')))
    pdfmetrics.registerFont(TTFont('Courier', str(FONT_ROOT / 'UbuntuMono-R.ttf')))

class Diagram:
    def __init__(self, w=510, h=480):
        self.w, self.h = w, h
        self.d = Drawing(w, h)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">', '<rect width="100%" height="100%" fill="white"/>']
    def text(self, x, y, text, size=10, color=INK, anchor='middle', bold=False):
        self.d.add(String(x, self.h-y, text, fontName='Helvetica-Bold' if bold else 'Helvetica', fontSize=size, fillColor=colors.HexColor(color), textAnchor=anchor))
        self.svg.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{"bold" if bold else "normal"}" fill="{color}">{html.escape(text)}</text>')
    def box(self, x, y, w, h, title, lines=(), proposed=False):
        stroke = TEAL if proposed else NAVY
        fill = '#E9F8F5' if proposed else PALE
        self.d.add(Rect(x,self.h-y-h,w,h,rx=6,ry=6,fillColor=colors.HexColor(fill),strokeColor=colors.HexColor(stroke),strokeWidth=1.1))
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}"/>')
        self.text(x+w/2,y+19,title,10.5,stroke,bold=True)
        for i, line in enumerate(lines): self.text(x+w/2,y+36+i*13,line,9)
    def arrow(self, points, label=None, lx=None, ly=None, color=MUTED, dashed=False):
        for (x1,y1),(x2,y2) in zip(points,points[1:]):
            line=Line(x1,self.h-y1,x2,self.h-y2,strokeColor=colors.HexColor(color),strokeWidth=1.2)
            if dashed: line.strokeDashArray=[4,3]
            self.d.add(line)
        x,y=points[-1]; px,py=points[-2]
        import math
        a=math.atan2(y-py,x-px); s=5
        pts=[x,y,x-s*math.cos(a)+s*.5*math.sin(a),y-s*math.sin(a)-s*.5*math.cos(a),x-s*math.cos(a)-s*.5*math.sin(a),y-s*math.sin(a)+s*.5*math.cos(a)]
        self.d.add(Polygon([v if i%2==0 else self.h-v for i,v in enumerate(pts)],fillColor=colors.HexColor(color),strokeColor=colors.HexColor(color)))
        self.svg.append(f'<polyline points="{" ".join(f"{a},{b}" for a,b in points)}" fill="none" stroke="{color}" stroke-width="1.2" {"stroke-dasharray=\"4 3\"" if dashed else ""}/>')
        self.svg.append(f'<polygon points="{" ".join(f"{pts[i]},{pts[i+1]}" for i in range(0,6,2))}" fill="{color}"/>')
        if label: self.text(lx,ly,label,8,color)
    def save(self, name):
        (ASSETS/f'{name}.svg').write_text('\n'.join(self.svg+['</svg>']))
        return self.d

def architecture():
    g=Diagram(h=540)
    g.text(255,14,'Existing service + proposed funding evidence layer',12,NAVY,bold=True)
    g.box(155,30,200,56,'Streamlit dashboard',['Banking, alerts, DBMS, ML pages'])
    g.box(155,112,200,56,'FastAPI + transfer service',['Validation and ordered row locks'])
    g.arrow([(255,86),(255,112)],'REST',285,102)
    g.box(155,196,200,69,'Atomic transfer boundary',['Debit / credit + transaction row','Model inference + stored prediction'])
    g.arrow([(255,168),(255,196)])
    g.box(0,294,145,81,'Existing scoring',['Indexed history / behaviour','PaySim baseline adapter','Raw ML probability retained'])
    g.box(178,294,155,81,'PostgreSQL',['Constraints, FKs, indexes','Alert + audit triggers','Commit or full rollback'])
    g.box(365,294,145,81,'Proposed: FABC',['Ordered ledger entries','Recent-funding bounds','Evidence certificate'],True)
    g.arrow([(185,265),(72,282),(72,294)])
    g.arrow([(255,265),(255,294)])
    g.arrow([(325,265),(437,282),(437,294)],color=TEAL,dashed=True)
    g.arrow([(145,335),(178,335)])
    g.arrow([(365,335),(333,335)],color=TEAL,dashed=True)
    g.box(155,404,200,56,'Persisted analyst evidence',['Prediction, alert, audit; proposed bounds'])
    g.arrow([(255,375),(255,404)])
    g.text(255,484,'All essential writes commit together; FLAGGED still moves funds.',10,NAVY)
    g.text(255,503,'Separate batch path: PaySim -> features / graph -> train -> artifacts.',9,MUTED)
    g.text(255,522,'Navy = existing   |   Teal / dashed = proposed, not implemented',9,TEAL)
    return g.save('project_architecture')

def existing_er():
    g=Diagram(h=490)
    g.box(171,8,168,62,'CUSTOMERS',['PK customer_id','UK email'])
    g.box(0,105,155,75,'ACCOUNTS',['PK account_id','FK customer_id','balance, currency'])
    g.box(355,105,155,75,'DEVICES',['PK device_id','FK customer_id','UK device_identifier'])
    g.arrow([(190,70),(77,88),(77,105)],'1 : 0..N owns',85,78)
    g.arrow([(320,70),(432,88),(432,105)],'1 : 0..N registers',425,78)
    g.box(170,212,170,88,'TRANSACTIONS',['PK transaction_id','FK source / destination','FK customer / optional device','amount + balance snapshots'])
    g.arrow([(255,70),(255,212)],'1 : 0..N',285,150)
    g.arrow([(77,180),(77,250),(170,250)],'source 1 : 0..N',39,218)
    g.arrow([(105,180),(105,281),(170,281)],'dest. 1 : 0..N',77,300)
    g.arrow([(432,180),(432,256),(340,256)],'0..1 : 0..N',469,216)
    g.box(170,333,170,62,'FRAUD_PREDICTIONS',['PK prediction_id','FK / UK transaction_id'])
    g.arrow([(255,300),(255,333)],'1 : 0..1',285,320)
    g.box(170,426,170,62,'FRAUD_ALERTS',['PK alert_id; FK transaction_id','FK / UK prediction_id'])
    g.arrow([(255,395),(255,426)],'1 : 0..1',285,414)
    g.box(0,358,145,75,'AUDIT_LOGS',['PK audit_id','table_name + record_id','No polymorphic FK'])
    g.box(365,358,145,75,'RISK_SETTINGS',['PK settings_id = 1','fraud_threshold','Policy; no entity FK'])
    return g.save('database_existing')

def proposed_er():
    g=Diagram(h=405)
    g.box(0,10,175,70,'ACCOUNTS (existing)',['PK account_id','Proposed: ledger_seq'],True)
    g.box(335,10,175,70,'TRANSACTIONS (existing)',['PK transaction_id','Immutable monetary facts'])
    g.box(151,121,208,88,'LEDGER_ENTRIES (new)',['PK (account_id, seq)','FK account_id / transaction_id','side, amount, before / after','recorded_at, payload_hash'],True)
    g.arrow([(87,80),(87,147),(151,147)],'1 : 0..N',82,111,color=TEAL)
    g.arrow([(422,80),(422,147),(359,147)],'1 : exactly 2*',463,111,color=TEAL)
    g.box(0,260,222,101,'FLOW_CERTIFICATES (new)',['PK certificate_id','FK / UK transaction_id','opening balance, seq range, window','lower / upper amounts, status','algorithm + policy versions, hash'],True)
    g.box(287,260,223,101,'CERTIFICATE_EVIDENCE (new)',['PK (certificate_id, account_id, seq)','FK certificate_id','Composite FK (account_id, seq)','ordinal, role; UK (cert, ordinal)'],True)
    g.arrow([(422,80),(497,80),(497,232),(111,232),(111,260)],'transaction 1 : 0..1 certificate',280,226,color=TEAL)
    g.arrow([(222,312),(287,312)],'1 : 0..N',255,302,color=TEAL)
    g.arrow([(309,209),(399,240),(399,260)],'entry 1 : 0..N',450,249,color=TEAL)
    g.text(255,385,'* Exactly two entries is a proposed deferred check / service invariant.',9,MUTED)
    g.text(255,401,'No new schema objects are installed by this documentation change.',9,TEAL)
    g.d.scale(0.86,0.86)
    g.d.width=438.6
    g.d.height=348.3
    # SVG keeps its full layout; PDF uses a smaller, centered vector drawing.
    return g.save('database_proposed')

ARCH, ER, NEW_ER = architecture(), existing_er(), proposed_er()

pages=[]
def page(title, subtitle, blocks): pages.append((title,subtitle,blocks))
def p(text): return ('p',text)
def h(text): return ('h',text)
def table(headers, rows, widths=None): return ('table',headers,rows,widths)
def code(text): return ('code',text)
def diagram(name): return ('diagram',name)
def note(text): return ('note',text)

page('FraudDetectAI', 'A DBMS project with an evidence-first fraud detection extension', [
    h('Proposed novelty: Funding Ambiguity Bounds Certificate (FABC)'),
    p('A transaction-consistent method that calculates how much of an outgoing payment must, and how much could, be funded by recent incoming transfers. It stores the answer with the exact ledger evidence needed to replay it.'),
    note('Academic proposal | 12 October 2026 | Existing system reviewed against repository source. FABC is a proposed extension; this report does not claim it has been implemented, benchmarked or proven patentable.'),
    h('The project in one paragraph'),
    p('Customers own bank accounts and registered devices. A FastAPI service validates internal transfers, locks affected rows, changes balances, runs a fitted fraud model and saves a prediction. PostgreSQL creates alerts and redacted audit records through triggers. Streamlit displays banking operations and investigation views. A separate PaySim pipeline trains transaction-only and graph-enhanced models.'),
    h('Why this is a useful addition'),
    p('Fast receipt-and-forward behaviour can indicate a pass-through account, but it also occurs in legitimate collections. Money in an account is fungible: timing alone cannot establish which receipt funded a payment. FABC expresses that uncertainty explicitly and turns the explanation into a reproducible database record.'),
    table(['Pages','Contents'],[['2-3','Existing project, finance concepts and proposed contribution'],['4-6','System architecture and existing / proposed database relations'],['7-9','Exact algorithm, examples, SQL and transaction protocol'],['10-12','DBMS concepts, implementation roadmap and evaluation'],['13-14','Prior art, patent framing, references and viva explanation']]),
])
page('01 / What the project already does', 'Existing implementation, without overstating its capabilities', [
    table(['Layer','Responsibility and source'],[
        ['Interface','Streamlit banking, DBMS demonstration and original ML analysis pages.'],
        ['API','FastAPI routes and validated request schemas in app/api and app/schemas.py.'],
        ['Transfer service','app/services/transactions.py: ownership, status, balance and currency checks; ordered account locks; atomic persistence.'],
        ['Online detection','Existing fitted PaySim baseline through app/services/inference.py; separate SQL behaviour features and heuristic risk.'],
        ['Database','SQLAlchemy entities, Alembic migrations, PostgreSQL triggers, audit logs, views, indexes and functions. SQLite is a local fallback.'],
        ['Offline ML','src/fraudgraph: validation, feature engineering, NetworkX graph, LR / RF / XGBoost, evaluation and explanations.'],
    ],[110,400]),
    h('One transfer, one atomic outcome'),
    p('The service locks the initiating customer and both accounts, writes the debit and credit snapshots, queries historical behaviour and runs inference. It stores raw model probability and final risk; prediction insertion invokes the alert trigger. Essential failures roll back the balances, transaction, prediction, alerts and audits together.'),
    p('Current risk = max(model_probability, 0.9 x behaviour_score). This is an alert heuristic, not a calibrated probability. FRAUD and SUSPICIOUS are workflow labels, not established facts about criminal activity. A FLAGGED transfer still posts money; the application does not implement a payment hold.'),
    h('Limits that matter to the proposal'),
    p('Only same-currency internal transfers are supported. The live API uses a baseline model, not the offline graph artifact. Full-graph aggregates and fraud-rate features can leak future information or labels. PaySim training is not validation on real bank customers. SQLite cannot demonstrate PostgreSQL row-level locks or stored functions.'),
])
page('02 / Novelty and financial reasoning', 'A precise, feasible contribution to investigate', [
    h('Research question'),
    p('Can a database produce an exact, replayable interval for the recent-money share of a transfer, and use a high unavoidable share to prioritize review while controlling false alerts and transaction latency?'),
    table(['Concept','Meaning in this project'],[
        ['Fungibility','An account balance does not label individual rupees by origin. Several allocations can explain the same ledger.'],
        ['Recent funding','Credits recorded within a chosen window before the target debit; recent does not mean illegal.'],
        ['Lower bound','The amount that must come from recent credits even if older funds are spent first wherever possible.'],
        ['Upper bound','The amount that could come from recent credits under another feasible allocation.'],
        ['Ambiguity width','Upper minus lower, divided by payment amount. A wide interval weakens attribution claims.'],
        ['Certificate','A stored result, policy version, ledger sequence boundary and ordered evidence, committed with the transfer.'],
    ],[110,400]),
    h('The candidate contribution'),
    p('Combine a one-account, chronological balance-conservation algorithm with a database protocol that binds its bounds to an immutable ledger prefix. Keep ML probability separate. Expose the lower bound, upper bound and data-completeness status to an analyst rather than inventing a unique funds path.'),
    h('Why it is doable'),
    p('The minimum version needs three tables, a per-account sequence counter, one indexed ordered history query and an O(n) Decimal algorithm. It uses the existing FastAPI, SQLAlchemy, Alembic, PostgreSQL and Streamlit stack; no GNN, blockchain or new distributed service is needed.'),
    note('The interval mathematics and transactional techniques may already be known. Academic distinctiveness is a hypothesis about their integration and evaluation in this system; patent novelty must survive a wider search and claim comparison. [1-4]'),
])
page('03 / System architecture', 'Existing components and the proposed extension are explicitly marked', [
    diagram('architecture'),
    p('FABC executes inside the existing transfer boundary after locks and before final persistence. Its history comes from the source account ledger. The proposal stores evidence alongside the ordinary prediction, while the existing alert and audit mechanism continues to operate.'),
])
page('04 / Existing database relationships', 'Actual entities and constraints in app/db/models.py', [
    diagram('existing_er'),
    p('Arrows point from referenced parent to child; labels show parent : child cardinality. A device is optional on a transaction. Source and destination are distinct account roles. Audit logs and risk settings are intentionally outside the entity FK chain.'),
    p('The schema allows at most one prediction per transaction and at most one alert per prediction. Exactly one prediction on a completed service transfer is an application invariant. Composite FKs enforce source-account ownership, device ownership and agreement between an alert and its prediction / transaction.'),
])
page('05 / Proposed schema and relationships', 'New tables for ordering, evidence and reproducibility', [
    diagram('proposed_er'),
    table(['Proposed object','Key constraints and role'],[
        ['accounts.ledger_seq','A BIGINT counter advanced under the account lock. Orders every credit / debit on that account; not a global commit sequence.'],
        ['ledger_entries','PK (account_id, seq); FK to account and transfer; UNIQUE(transaction_id, side). side is DEBIT or CREDIT. Positive NUMERIC amount, nonnegative balances and arithmetic checks.'],
        ['flow_certificates','Unique transaction FK, source account, opening sequence / balance, target debit sequence, window bounds, lower / upper amounts, status, evidence digest and versioned parameters.'],
        ['certificate_evidence','FK to certificate; composite FK to ledger entry. Ordered entries with OPENING_ANCHOR, HISTORY or TARGET roles. Store every required entry, not just selected suspicious receipts.'],
    ],[120,390]),
    p('For a valid certificate enforce 0 <= lower <= upper <= target amount. A composite FK to a UNIQUE(transaction_id, account_id, side, seq) ledger key can bind the target to the actual source DEBIT. Cross-row conservation and two-entry completeness need deferred constraint triggers or a restricted write service; a row CHECK alone is insufficient.'),
])
page('06 / The exact bounds algorithm', 'One account, one fixed window, all posted movements', [
    h('Inputs and assumptions'),
    p('Let x be the proposed debit. Let B be the balance at the start of the window. Treat that opening balance as old money, even if its origin is unknown. Read all account entries in sequence after the window boundary and before the target debit. All credits in this interval are recent. No overdrafts, unrecorded balance changes, fees, FX or missing movements are allowed.'),
    p('L and U are the minimum and maximum recent-money balance that could remain. Start L = U = 0. Track B exactly in Decimal or integer minor units. Sequence order governs causality; the server-recorded window determines which credits qualify.'),
    code('For a credit c:\n    B = B + c\n    L = L + c\n    U = U + c\n\nFor an earlier debit d (require 0 < d <= B):\n    L = max(0, L - d)\n    U = min(U, B - d)\n    B = B - d\n\nBefore target debit x (require 0 < x <= B):\n    lower_amount = max(0, x - (B - L))\n    upper_amount = min(x, U)\n    lower_share = lower_amount / x\n    upper_share = upper_amount / x'),
    h('Why the bounds are exact under these assumptions'),
    p('At a debit, spending recent funds first minimizes the recent balance left; spending old funds first maximizes it. Both choices are feasible because funds are fungible and balances stay nonnegative. Induction over credits and debits gives attainable endpoints L and U. For the target, at most B-L old money can be available, and at most U recent money can be available.'),
    p('The scan takes O(n) arithmetic operations with O(1) working state; keeping n evidence rows costs O(n) storage. A B-tree prefix lookup adds query overhead. Individual payment intervals are marginal bounds: their upper amounts must not be summed as if jointly attainable.'),
    note('MVP scope is one account and one window. Multi-hop source attribution requires additional shared-capacity constraints and is future work, not a property of this algorithm.'),
])
page('07 / Worked examples and review policy', 'Concrete numbers, including an important benign counterexample', [
    h('Example A: recent money is unavoidable'),
    table(['Event','Balance B','Possible recent balance [L,U]'],[
        ['Window opens with INR 1,000','1,000','[0, 0]'],
        ['Credit INR 4,000 from A','5,000','[4,000, 4,000]'],
        ['Credit INR 3,000 from B','8,000','[7,000, 7,000]'],
        ['Credit INR 2,000 from C','10,000','[9,000, 9,000]'],
        ['Earlier debit INR 2,000','8,000','[7,000, 8,000]'],
        ['Target debit INR 7,500','Before debit: 8,000','Target recent amount: [6,500, 7,500]'],
    ],[225,95,190]),
    p('Lower share = 6,500 / 7,500 = 86.67%; upper share = 100%. At least INR 6,500 must be recently received money under every feasible allocation. Three incoming counterparties plus a fast onward payment makes this a candidate for pass-through review.'),
    h('Example B: a funded business account remains ambiguous'),
    p('Opening balance INR 100,000; recent receipts INR 9,000; target debit INR 7,500. The recent-funding interval is [0, 7,500], or [0%, 100%]. The account could pay entirely from older funds. A heuristic based only on nearby receipts might imply a linkage the ledger cannot establish.'),
    h('A transparent initial policy, not a probability'),
    p('For a course demo, request review when lower_share >= 0.80 AND at least three distinct incoming counterparties appear in a ten-minute window. These are starting parameters for evaluation, not regulatory thresholds. Store the flow result separately from model_probability and behaviour_score.'),
    p('A lower bound of zero does not prove innocence. A high lower bound does not prove fraud: merchant settlements, family collections and payroll accounts can show the same pattern. If evidence is incomplete, status is INCOMPLETE and bounds are NULL, not zero. A flow flag queues investigation; it does not silently block the transfer.'),
])
page('08 / SQL and transaction protocol', 'A concrete integration design for PostgreSQL', [
    h('Ordered evidence extraction (illustrative new schema)'),
    code('SELECT account_id, seq, transaction_id, side, amount,\n       balance_before, balance_after, recorded_at\nFROM ledger_entries\nWHERE account_id = :source_account\n  AND seq > :opening_seq\n  AND seq < :target_debit_seq\nORDER BY seq;\n\n-- Proposed supporting index:\nCREATE INDEX idx_ledger_account_recorded_seq\nON ledger_entries(account_id, recorded_at, seq);'),
    p('Find the first entry at or after window_start, using the same account prefix. The preceding entry is the opening anchor; its balance_after is the opening balance. If no movement occurs in the window, use the locked pre-transfer balance and the preceding sequence. Validate sequence continuity and every before / after snapshot. A missing anchor or balance gap makes the result INCOMPLETE.'),
    h('Commit protocol'),
    p('1. Begin a fresh database transaction. Keep the current customer lock and globally ordered account locks. All movement writers must acquire the affected account locks before changing balances or allocating sequences.'),
    p('2. Allocate one new sequence on each account. Choose server recorded_at after acquiring locks; enforce nondecreasing timestamps per account. Store exactly one DEBIT and one CREDIT for the internal transfer. Event timestamps supplied by callers are metadata, not ledger ordering keys.'),
    p('3. Query the source prefix ending immediately before its new DEBIT. Compute bounds; save the certificate, opening anchor, full evidence membership and target reference. Preserve the ordinary inference result and version the flow policy.'),
    p('4. Save prediction and any review flag. Trigger audits and alerts; commit every essential write together. A failure aborts all writes. A proposed bounded scan cap returns INCOMPLETE with a reason and no numerical claim; it never computes a false exact bound from truncated history.'),
    note('Current locking is adequate only if every balance movement obeys the account-lock protocol. Direct SQL writers must be restricted. A separate multi-account graph scan would require a stable snapshot / serializable protocol and retries; sequences alone do not create a global snapshot. [5]'),
])
page('09 / DBMS concepts made visible', 'What to explain and demonstrate in an academic assessment', [
    table(['Concept','Concrete application and demonstration'],[
        ['Primary / foreign keys','Customer-account-device-transfer-prediction-alert chain; proposed composite ledger references prevent evidence from pointing to a nonexistent entry.'],
        ['Constraints','Nonnegative balances, positive amounts, distinct accounts, ownership FKs, monetary arithmetic and score ranges. Try an invalid insert and show rejection.'],
        ['Normalization','Separate customer, account, device, prediction and alert facts. Proposed certificates separate a derived result from a many-to-many evidence relation.'],
        ['Denormalization','Existing transaction.customer_id and alert.transaction_id are deliberate redundant navigation keys; composite FKs preserve agreement. Do not claim strict 3NF for every table.'],
        ['Atomicity','Inject an inference / certificate write failure and show that all balances and associated rows roll back.'],
        ['Isolation','Run opposite-direction or simultaneous debit requests; show ordered row locks and absence of double spending. Account sequences order new ledger facts.'],
        ['Consistency / durability','Balance checks and ledger continuity preserve valid state; committed data remains after reconnect / database restart.'],
        ['Triggers / procedures','Existing alert and audit triggers, PostgreSQL velocity/statistics functions; proposed deferred check for exactly two ledger entries.'],
        ['Indexes / query plans','Existing customer-time and risk indexes; proposed account-time-sequence index. Use EXPLAIN ANALYZE at meaningful volumes.'],
        ['Views / joins','Existing suspicious-transaction and customer-risk views; proposed certificate detail view joins results and evidence.'],
    ],[118,392]),
    h('Reproducibility and retention'),
    p('Hash canonical ordered evidence plus the opening balance, target, window and algorithm / policy version. Use fixed decimal strings, UTC timestamp formatting and a specified field order. A digest detects mismatched replay inputs; it is not proof against a privileged administrator who can rewrite data and hashes. Append-only permissions and backups remain necessary.'),
    p('Keep ledger monetary facts immutable; later alert reviews are separate workflow events. Existing demo cleanup deletes disposable rows, so the new ledger should use a dedicated demo dataset or explicit retention handling. Never silently cascade-delete evidence used by a certificate.'),
])
page('10 / A feasible implementation roadmap', 'Estimated 2-3 weeks for a small team; adjust to course deadlines', [
    table(['Milestone','Work and acceptance evidence'],[
        ['1. Schema and ordering\nDays 1-3','New Alembic migration; ledger counter; append-only entries; opening anchors; indexes. Seed reproducible account histories. Existing migrations remain untouched.'],
        ['2. Bounds engine\nDays 4-6','app/services/flow_bounds.py with Decimal math, contiguous-prefix validation and clear result statuses. Verify against exhaustive small integer allocations.'],
        ['3. Atomic integration\nDays 7-10','Extend process_transfer to write ledger and certificate in the same transaction. Add unique idempotency keys for retry-safe requests; injection and concurrency checks.'],
        ['4. Analyst interface\nDays 11-13','Display lower / upper shares, opening balance, chronological evidence and policy version. Add separate flow review flag and a certificate replay endpoint.'],
        ['5. Evaluation / viva\nDays 14-18','Compare baselines, run ablations and query-plan measurements; export results and rehearse rollback / replay demonstration.'],
    ],[130,380]),
    h('Minimum viable scope'),
    p('One account, one ten-minute window, internal transfers only, exact interval scan and persisted evidence. Start with a separate flow flag on the certificate. If integrating flow flags into fraud_alerts, add a new versioned trigger policy and preserve the existing one-alert-per-prediction constraint; merge reasons instead of inserting duplicate alerts.'),
    h('Extension points'),
    p('New models belong in app/db/models.py through a new migration. Extend app/services/transactions.py after locks and before commit. Add a flow detail view on the Banking page. Use a separate synthetic evaluation script with saved random seeds; avoid changing the baseline model feature contract.'),
    h('Engineering tradeoff'),
    p('A fixed-window scan is easier to verify than a cache whose boundary expires continuously. Measure the scan first. Set an explicit history cap and surface INCOMPLETE when exceeded. Checkpoints or incremental bounds should come later, with exact window-expiry logic and replay equivalence tests.'),
    note('This change delivers the design document and diagrams. It does not install the proposed schema or alter transfer behaviour. The effort estimate is a planning assumption, not a delivery guarantee.'),
])
page('11 / Evaluation that can support the claim', 'Separate correctness, detection utility and database cost', [
    h('Data and leakage controls'),
    p('Generate balance-valid internal ledgers with planted pass-through patterns and matched benign patterns: merchant aggregation, salaries, family pooling, refunds, long-lived balances and split payments. Preserve seeds and withheld labels. These experiments test designed scenarios, not real-bank generalization.'),
    p('PaySim can benchmark the existing transaction model, but it does not supply the full local ledger protocol, application devices or certified funding provenance. Its step is hourly, so it cannot establish ten-minute timing. Run any PaySim interval study at its actual time resolution and validate ledger completeness; otherwise mark it unsupported.'),
    p('Use chronological train / validation / test splits. Select flow windows and thresholds on validation only. At inference, exclude target / future graph aggregates and unavailable fraud labels. Compare against a repaired historical graph baseline, not the existing potentially leaked full graph.'),
    table(['Experiment','Evidence to report'],[
        ['Correctness','Exhaustive allocation oracle on small integer histories; lower / upper attainability; boundary times, prior debits, gaps, opening anchors and zero-history cases.'],
        ['Detection baselines','Current ML + behaviour; velocity + fan-in heuristic; FIFO attribution policy; FABC lower-bound flag. Keep data and review budgets identical.'],
        ['Ablations','Upper-bound-only vs lower-bound flag; remove counterparty condition; vary opening balance and window; same engine with / without persisted certificate for system cost.'],
        ['Detection metrics','Precision, recall, average precision where a ranking exists, false alerts per 1,000 benign transfers, recall at a fixed review budget and alerted amount.'],
        ['Database metrics','p50 / p95 / p99 transfer latency; scanned rows; certificate bytes; lock wait time; throughput; rollback failures; exact replay agreement.'],
        ['Concurrency / recovery','Simultaneous credits/debits, failed inference, certificate failure, retry/idempotency, reversal as a new movement and restart persistence.'],
    ],[120,390]),
    note('No improvement figures are asserted. A successful research outcome may be a more faithful explanation at similar detection quality; measure the cost of that explanation as well as its benefit.'),
])
page('12 / Prior art and patent framing', 'A bounded preliminary search, not a patentability opinion', [
    table(['Reference','Known contribution / relevance'],[
        ['[1] FlowScope, AAAI 2020','Detects money-laundering flows using multipartite transaction graphs. Flow-based detection itself is established prior art.'],
        ['[2] US11854091B1','Transaction tracing includes FIFO attribution and graph transformation. Generic funds tracing or putting it in a database is not a defensible new claim by itself.'],
        ['[3-4] IP India','Novelty, inventive step and exclusions matter. Section 3(k) excludes mathematical / business methods, computer programmes per se and algorithms; CRI Guidelines 2025 inform examination.'],
        ['[5] PostgreSQL isolation','Row locks, snapshots, serialization handling and transactional persistence are established database mechanisms.'],
    ],[135,375]),
    h('A narrower invention hypothesis to investigate'),
    p('A database processing method that generates attainable recent-funding bounds from an ordered account ledger, binds each decision to a validated evidence prefix and atomically persists the bounds certificate with the financial movement. The proposed technical objective is consistent, replayable evidence under concurrent writes with bounded query cost.'),
    p('The question is whether this particular combination is new and non-obvious compared with attribution intervals, taint analysis, provenance certificates and transaction-consistent incremental analytics. The formula, hash, lock or dashboard alone should not be presented as an invention. A faster query, better consistency or reduced evidence storage must be implemented and measured before asserting a technical advantage.'),
    h('What remains before any filing decision'),
    p('Search patent families and papers for funding-source bounds, fungible-flow attribution, lower / upper taint bounds, flow-conservation intervals, provenance snapshots and ledger certificates. Compare independent claims and priority dates; check Indian and international equivalents. Document the actual implementation and experimental technical effects, then review eligibility and disclosure timing with the institution IP cell or a patent professional.'),
    note('Recommended academic positioning: an uncertainty-aware, transaction-consistent evidence extension for a banking DBMS. Potentially worth an invention disclosure after validation; patent eligibility, novelty, freedom to operate and grant prospects remain unresolved.'),
])
page('13 / References and viva explanation', 'Primary sources checked on 12 October 2026', [
    p('[1] Li et al. FlowScope: Spotting Money Laundering Based on Graphs. AAAI 2020, 34(4), 4731-4738. DOI: 10.1609/aaai.v34i04.5906. <link href="https://ojs.aaai.org/index.php/AAAI/article/view/5906" color="#087F8C">Publisher record</link>.'),
    p('[2] Systems and methods for transaction tracing. US11854091B1, published 26 December 2023. <link href="https://patents.google.com/patent/US11854091B1/en" color="#087F8C">Patent text and claims</link>. Cited for technical disclosure, not an independently verified legal-status assessment.'),
    p('[3] Intellectual Property India. Patents Act, Section 3(k), and Basics of Patents. <link href="https://www.ipindia.gov.in/acts/patent-act-1970/section-3" color="#087F8C">Section 3</link>; <link href="https://ipindia.gov.in/basics-of-patents" color="#087F8C">Patent basics</link>.'),
    p('[4] CGPDTM. Guidelines for Examination of Computer Related Inventions (CRIs), 2025. <link href="https://ipindia.gov.in/resource/patents-resources-guidelines" color="#087F8C">Official guidelines catalog</link>. Release announcement: <link href="https://www.pib.gov.in/PressReleasePage.aspx?PRID=2149719" color="#087F8C">Press Information Bureau</link>.'),
    p('[5] PostgreSQL documentation. Transaction Isolation. <link href="https://www.postgresql.org/docs/current/transaction-iso.html" color="#087F8C">Official documentation</link>. Stronger isolation can require retries; an account sequence is not a global transaction snapshot.'),
    h('Repository evidence reviewed'),
    p('README.md; docs/ARCHITECTURE.md; docs/DATABASE_DESIGN.md; app/db/models.py; app/services/transactions.py; app/services/features.py; src/fraudgraph/models/train_graph_enhanced.py. These establish the current system and its limitations. No existing model metrics are reproduced as evidence of the new proposal.'),
    h('A 60-second project explanation'),
    p('"Our project is a relational banking system with AI-assisted fraud review. Transfers, predictions, alerts and audit history commit together, and constraints protect account ownership and balances. Our proposed addition asks how much of a payment must come from recent receipts. Because money is mixed, we compute an interval rather than assert a single source. We save that interval with the exact ordered ledger evidence so a reviewer can reproduce it. We will test correctness, benign counterexamples, review quality and database overhead. This is a research proposal; we do not claim a patent or proven detection improvement."'),
    h('The strongest demonstration'),
    p('Run the two numerical examples; show a saved bounds certificate and replay; then inject a write failure and demonstrate complete rollback. Finally run concurrent transfers and verify that every certificate refers to a valid source-account prefix. Label these as future acceptance demonstrations until the extension is built.'),
])

styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleX', fontName='Helvetica-Bold', fontSize=25, leading=29, textColor=colors.HexColor(NAVY), spaceAfter=8))
styles.add(ParagraphStyle(name='SubX', fontName='Helvetica', fontSize=11, leading=15, textColor=colors.HexColor(TEAL), spaceAfter=18))
styles.add(ParagraphStyle(name='BodyX', fontName='Helvetica', fontSize=10, leading=14.4, textColor=colors.HexColor(INK), spaceAfter=10))
styles.add(ParagraphStyle(name='HeadX', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor(NAVY), spaceBefore=5, spaceAfter=8))
styles.add(ParagraphStyle(name='NoteX', fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor(MUTED), spaceAfter=10))
styles.add(ParagraphStyle(name='CodeX', fontName='Courier', fontSize=8.5, leading=12, textColor=colors.HexColor(INK), backColor=colors.HexColor(PALE), borderPadding=10, spaceBefore=5, spaceAfter=14))
styles.add(ParagraphStyle(name='CellX', fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor(INK)))
styles.add(ParagraphStyle(name='CellHeadX', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.white))

story=[]
md=['# FraudDetectAI: academic project and novelty proposal','', '> Status: FABC is proposed, not implemented. Generated PDF and diagrams are rebuilt with scripts/create_project_proposal.py.','']
ds={'architecture':ARCH,'existing_er':ER,'proposed_er':NEW_ER}
for idx,(title,sub,blocks) in enumerate(pages):
    if idx: story.append(PageBreak())
    story.extend([Paragraph(title,styles['TitleX']),Paragraph(sub,styles['SubX'])])
    md.extend(['## '+title,'',sub,''])
    for b in blocks:
        if b[0] in ('p','h','note'):
            story.append(Paragraph(b[1],styles[{'p':'BodyX','h':'HeadX','note':'NoteX'}[b[0]]]))
            md.extend([('### ' if b[0]=='h' else '> ' if b[0]=='note' else '')+b[1],''])
        elif b[0]=='code':
            story.append(Paragraph(html.escape(b[1]).replace(' ','&nbsp;').replace('\n','<br/>'),styles['CodeX']))
            md.extend(['```text',b[1],'```',''])
        elif b[0]=='table':
            data=[[Paragraph(str(t).replace('\n','<br/>'),styles['CellHeadX']) for t in b[1]]]+[[Paragraph(str(t).replace('\n','<br/>'),styles['CellX']) for t in row] for row in b[2]]
            widths=b[3] or [510/len(b[1])]*len(b[1])
            t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(NAVY)),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor(PALE),colors.white]),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor(TEAL))]))
            story.extend([t,Spacer(1,12)])
            md.extend(['| '+' | '.join(b[1])+' |','| '+' | '.join(['---']*len(b[1]))+' |']+['| '+' | '.join(row).replace('\n','<br>')+' |' for row in b[2]]+[''])
        elif b[0]=='diagram':
            story.extend([ds[b[1]],Spacer(1,12)])
            names={'architecture':'project_architecture','existing_er':'database_existing','proposed_er':'database_proposed'}
            md.extend([f'![{b[1]}](diagrams/{names[b[1]]}.svg)',''])

def footer(canvas,doc):
    canvas.setStrokeColor(colors.HexColor('#C8D6DF')); canvas.line(42,39,552,39)
    canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor(MUTED))
    canvas.drawString(42,25,'FraudDetectAI | Academic design proposal | 12 October 2026')
    canvas.drawRightString(552,25,str(doc.page))
    canvas.setTitle('FraudDetectAI - Project, Novelty and Database Architecture')
    canvas.setAuthor('FraudDetectAI academic project')

target=OUT/'FraudDetectAI_Project_Novelty_and_Architecture.pdf'
doc=SimpleDocTemplate(str(target),pagesize=(595.28,841.89),rightMargin=42,leftMargin=42,topMargin=43,bottomMargin=54)
doc.build(story,onFirstPage=footer,onLaterPages=footer)
(ROOT/'docs/PROJECT_NOVELTY_PROPOSAL.md').write_text('\n'.join(md))
print(target)
