import asyncio
import sys
import os

# Add the app directory to sys.path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from app.core.database import async_session_maker, engine
from app.models import Plan, TemplateContract, Agent
from sqlalchemy.ext.asyncio import AsyncSession

async def seed_data():
    print("Starting database seeding...")
    async with async_session_maker() as db:
        # 1. Seed Plans
        # NOTE: `stripe_price_id` for paid plans is a placeholder until the
        # operator runs `scripts/bootstrap_stripe_products.py` against their
        # Stripe Test-mode account, then pastes the real `price_xxx` IDs here
        # and re-runs this seed (UPSERT updates the row in place).
        plans_data = [
            {
                "id": 1,
                "title": "Free",
                "description": "Prueba básica para redactar tus primeros contratos.",
                "price": 0.0,
                "contracts_included": 2,
                "time_subscription": "lifetime",
                "plan_type": "subscription",
                "currency": "usd",
                "is_active": True,
                "stripe_price_id": None,
                "stripe_product_id": None,
            },
            {
                "id": 2,
                "title": "Pro",
                "description": "Ideal para profesionales e independientes.",
                "price": 29.99,
                "contracts_included": 15,
                "time_subscription": "monthly",
                "plan_type": "subscription",
                "currency": "usd",
                "is_active": True,
                "stripe_price_id": "price_1TZKKkRaNX53Ajh7tWGd5EmD",
                "stripe_product_id": None,
            },
            {
                "id": 3,
                "title": "Enterprise",
                "description": "Contratos ilimitados para grandes empresas.",
                "price": 99.99,
                "contracts_included": 1000,
                "time_subscription": "monthly",
                "plan_type": "subscription",
                "currency": "usd",
                "is_active": True,
                "stripe_price_id": "price_1TZKKlRaNX53Ajh7Te0vhy9m",
                "stripe_product_id": None,
            },
            {
                "id": 4,
                "title": "Credit Pack Small",
                "description": "10 créditos one-time para uso flexible.",
                "price": 9.99,
                "contracts_included": 10,
                "time_subscription": "one_time",
                "plan_type": "credit_pack",
                "currency": "usd",
                "is_active": True,
                "stripe_price_id": "price_1TZKKmRaNX53Ajh7Iyq2AURp",
                "stripe_product_id": None,
            },
            {
                "id": 5,
                "title": "Credit Pack Medium",
                "description": "50 créditos one-time para uso flexible.",
                "price": 29.99,
                "contracts_included": 50,
                "time_subscription": "one_time",
                "plan_type": "credit_pack",
                "currency": "usd",
                "is_active": True,
                "stripe_price_id": "price_1TZKKoRaNX53Ajh77BZyoMJI",
                "stripe_product_id": None,
            },
            {
                "id": 6,
                "title": "Credit Pack Large",
                "description": "200 créditos one-time para uso flexible.",
                "price": 79.99,
                "contracts_included": 200,
                "time_subscription": "one_time",
                "plan_type": "credit_pack",
                "currency": "usd",
                "is_active": True,
                "stripe_price_id": "price_1TZKKqRaNX53Ajh7IaIEalQ6",
                "stripe_product_id": None,
            },
        ]

        for p_data in plans_data:
            result = await db.execute(select(Plan).where(Plan.id == p_data["id"]))
            existing = result.scalar_one_or_none()
            if existing is None:
                plan = Plan(**p_data)
                db.add(plan)
                print(f"Added plan: {p_data['title']}")
            else:
                # UPSERT: keep id stable, refresh every other column so the seed
                # is the source of truth for pricing / Stripe identifiers.
                for key, value in p_data.items():
                    if key == "id":
                        continue
                    setattr(existing, key, value)
                print(f"Updated plan: {p_data['title']}")

        # =====================================================================
        # 2. Seed / Update Template Contracts
        # NOTE: Uses UPSERT logic — updates rules/description if template exists.
        # Based on real contract examples from /Contratos/ folder.
        # =====================================================================
        templates_data = [
            # -----------------------------------------------------------------
            # ID 1 — IMMIGRATION FORM PREPARATION AGREEMENT
            # Based on: Gocontract- IMMIGRATION FORM PREPARATION AGREEMENT.docx
            # UI: Workforce Immigration → Immigration Legal Services Agreement
            # -----------------------------------------------------------------
            {
                "id": 1,
                "category": "immigration",
                "title": "Immigration Legal Services Agreement",
                "description": "Acuerdo de preparación de formularios migratorios. El proveedor de servicios NO es abogado. Asistencia clerical y administrativa únicamente.",
                "rules": """GENERATE AN "IMMIGRATION FORM PREPARATION AGREEMENT" WITH EXACTLY THIS STRUCTURE:

TITLE: "IMMIGRATION FORM PREPARATION AGREEMENT"

HEADER BLOCK:
This Immigration Form Preparation Agreement ("Agreement") is entered into on [agreementDate], by and between:
Service Provider: [contractorName], [contractorAddress]
Client: [clientName], [clientAddress]
Collectively referred to as the "Parties."

SECTION 1 — Purpose of Agreement:
The purpose of this Agreement is to define the terms under which the Service Provider will assist the Client with the preparation of immigration forms and document organization related to immigration filings.

SECTION 2 — Scope of Services:
The Service Provider agrees to provide the following services:
- Preparation of immigration forms based on information provided by the Client
- Assistance organizing supporting documentation
- Formatting and assembling application packages
- Administrative assistance related to immigration filings
The Service Provider may assist with forms filed before U.S. Citizenship and Immigration Services (USCIS) or other government agencies.
This Agreement covers the preparation of the following forms: [list each form from selectedImmigrationForms — use full USCIS form names]
[If additionalServicesDescription is provided, add: "Additional services: [additionalServicesDescription]"]

SECTION 3 — Disclaimer – No Legal Advice:
The Client acknowledges that the Service Provider IS NOT AN ATTORNEY and does NOT provide legal advice.
The services provided under this Agreement are LIMITED TO CLERICAL AND ADMINISTRATIVE ASSISTANCE in preparing immigration forms based on information provided by the Client.
The Service Provider does NOT provide:
- legal representation
- legal opinions
- legal strategy
- court representation
If legal advice is required, the Client should consult with a licensed immigration attorney.

SECTION 4 — Client Responsibility for Information:
The Client is SOLELY RESPONSIBLE for:
- providing complete and accurate information
- providing authentic documentation
- reviewing all forms before signing
The Service Provider relies entirely on the information provided by the Client.
The Client understands that submitting false or inaccurate information to government agencies may result in DENIAL of the application or other legal consequences.

SECTION 5 — Review and Signature of Forms:
The Client agrees to carefully review all prepared forms prior to signing.
The Client must sign all immigration forms before submission.
The Service Provider is not responsible for any errors resulting from incorrect information provided by the Client.

SECTION 6 — Government Filing Fees:
Government filing fees are SEPARATE from the Service Provider's fees.
All filing fees must be paid DIRECTLY to the appropriate government agency including U.S. Citizenship and Immigration Services (USCIS).
The Service Provider DOES NOT control government processing times.

SECTION 7 — Fees and Payment Terms:
Total Service Fee: $[totalServiceFee] [currency]
Payment terms:
- Initial payment due upon signing: $[initialPayment]
- Remaining balance due before delivery of final documents
[If isNonRefundable: "All fees are NON-REFUNDABLE once work has begun, except where required by law."]
[If govFeesDisclaimer: "Government filing fees are not included in the above amounts and must be paid separately."]

SECTION 8 — Limited Scope of Services:
This Agreement covers ONLY the preparation of immigration forms described in Section 2.
The Service Provider is NOT responsible for:
- legal analysis of eligibility
- representation in immigration court
- appeals or motions
- responding to Requests for Evidence (RFE)
Additional services require a separate written agreement.

SECTION 9 — Confidentiality:
[If confidentialityClause: "The Service Provider agrees to maintain strict confidentiality of the Client's personal information and immigration documents. Client information will not be disclosed to third parties without consent except as required to complete the preparation of forms."]

SECTION 10 — Termination:
Either Party may terminate this Agreement with written notice.
If the Agreement is terminated after work has begun, the Service Provider may retain fees for services already performed.

SECTION 11 — Limitation of Liability:
[If limitationOfLiability:] The Service Provider shall NOT be liable for:
- immigration decisions made by government agencies
- delays caused by government processing
- errors resulting from inaccurate information provided by the Client
Total liability shall not exceed the amount paid for services under this Agreement.

SECTION 12 — NO GUARANTEE CLAUSE (MANDATORY — ALWAYS INCLUDE):
THE SERVICE PROVIDER MAKES NO GUARANTEE OR REPRESENTATION REGARDING THE OUTCOME OF ANY IMMIGRATION APPLICATION OR USCIS DECISION. APPROVAL OF ANY APPLICATION IS SOLELY AT THE DISCRETION OF THE RELEVANT GOVERNMENT AGENCY.

SECTION 13 — Governing Law:
This Agreement shall be governed by the laws of the State of [immigrationGoverningState].
U.S. Federal immigration laws and USCIS regulations apply.

SECTION 14 — Entire Agreement:
This Agreement represents the entire understanding between the Parties and supersedes all prior discussions. Any modification must be made in writing and signed by both Parties.

SIGNATURE BLOCK:
Service Provider
Name: [contractorName]
Signature: _______________________
Date: ___________________________

Client
Name: [clientName]
Signature: _______________________
Date: ___________________________

MANDATORY RULES:
- The "No Legal Advice" disclaimer (Section 3) is NON-NEGOTIABLE and MUST appear verbatim.
- The "No Guarantee" clause (Section 12) is NON-NEGOTIABLE and MUST appear verbatim.
- Government filing fees MUST always be stated as separate and paid directly to USCIS.
- All fees must be stated as non-refundable once work has begun.
- JURISDICTION: US Federal Immigration Law (USCIS). State law per immigrationGoverningState field."""
            },

            # -----------------------------------------------------------------
            # ID 2 — TERMINATION AGREEMENT
            # Based on: Termination Agreement-Contractors Business Ops.docx
            # UI: Contractors Business Ops → Termination Agreement
            # -----------------------------------------------------------------
            {
                "id": 2,
                "category": "corporate",
                "subcategory": "hr",
                "title": "Termination Agreement",
                "description": "Acuerdo mutuo de terminación de contrato. Incluye liberación mutua, confidencialidad y disposiciones legales estándar.",
                "rules": """GENERATE A "TERMINATION AGREEMENT" WITH EXACTLY THIS STRUCTURE:

TITLE: "TERMINATION AGREEMENT"

HEADER BLOCK:
THIS TERMINATION AGREEMENT (the "Agreement") dated this [agreementDate].

BETWEEN:
[clientName] of [clientAddress]
and
[contractorName] of [contractorAddress]
(collectively the "Parties" and individually the "Party")

BACKGROUND:
A. The Parties are presently bound by the following contract (the "Contract") dated [originalContractDate]: [originalContractName].
[If originalContractDescription is provided: "B. Description of original contract: [originalContractDescription]."]
B. The Parties wish to terminate the Contract and resolve any and all rights and obligations arising out of the Contract.

IN CONSIDERATION OF and as a condition of the Parties entering into this Agreement and other valuable consideration, the receipt and sufficiency of which consideration is acknowledged, the Parties agree as follows:

TERMINATION:
1. By this Agreement the Parties terminate and cancel the Contract effective the [effectiveTerminationDate or agreementDate].
[Based on terminationType:
  - immediate: "The termination is effective immediately upon execution of this Agreement."
  - specificDate: "The termination is effective on [effectiveTerminationDate]."
  - conditional: "The termination is effective upon satisfaction of the conditions agreed upon by the Parties."]

OUTSTANDING OBLIGATIONS:
2. [If noFurtherObligations:] The Parties acknowledge by this Agreement that the consideration provided and received by each other is fair, just and reasonable and that no further consideration, compensation or obligation will be due, payable or owing with regard to the Contract as of the execution date of this Agreement.
[If includeSettlement:] Notwithstanding the foregoing, [clientName] agrees to pay [contractorName] a settlement amount of $[settlementAmount] USD, due within 30 days of the execution of this Agreement.

RELEASE:
3. [Based on releaseClauseType:]
- mutual: By this Agreement the Parties release each other from any and all claims, causes of action, demands and liabilities of whatever nature which either Party had in the past, has now or may have in the future arising from or related to the Contract.
- oneSided: [Specify which party releases the other] releases [the other party] from any and all claims arising from or related to the Contract.

CONFIDENTIALITY:
4. The Parties acknowledge and agree that all parties to this Agreement will keep completely confidential the terms and conditions of this Agreement, the Contract and any financial, operational or confidential information of any kind not already public.
[Based on terminationConfidentiality: specify duration — infinite / 1 year / 2 years / 3 years / 5 years]

GOVERNING LAW:
5. The Parties submit to the jurisdiction of the courts of the State of [governingState] for the enforcement of this Agreement or any arbitration award or decision arising from this Agreement. This Agreement will be enforced or construed according to the laws of the State of [governingState].

MISCELLANEOUS PROVISIONS:
6. Time is of the essence in this Agreement.
[If allowCounterparts:] 7. This Agreement may be executed in counterparts. Facsimile signatures are binding and are considered to be original signatures.
8. Headings are inserted for the convenience of the Parties only and are not to be considered when interpreting this Agreement. Words in the singular mean and include the plural and vice versa.
[If includeSeverability:] 9. If any term, covenant, condition or provision of this Agreement is held by a court of competent jurisdiction to be invalid, void or unenforceable, it is the Parties' intent that such provision be reduced in scope by the court only to the extent deemed necessary by that court to render the provision reasonable and enforceable and the remainder of the provisions of this Agreement will in no way be affected, impaired or invalidated as a result.
10. This Agreement contains the entire agreement between the Parties. All negotiations and understandings have been included in this Agreement.
11. This Agreement and the terms and conditions contained in this Agreement apply to and are binding upon the Parties and their respective successors, assigns, executors, administrators, beneficiaries and representatives.
12. Any notices or delivery required in this Agreement will be deemed completed when hand-delivered, delivered by agent, or seven (7) days after being placed in the post, postage prepaid, to the Parties at the addresses contained in this Agreement.
[If includeCumulativeRemedies:] 13. All of the rights, remedies and benefits provided by this Agreement will be cumulative and will not be exclusive of any other such rights, remedies and benefits allowed by law.
[If allowElectronicSignatures:] 14. Electronic signatures are legally binding and shall be considered equivalent to original handwritten signatures.

SIGNATURE BLOCK:
[clientName]
Signature: _______________________
Date: ___________________________

[contractorName]
Signature: _______________________
Date: ___________________________

MANDATORY RULES:
- The Mutual Release clause (Section 3) MUST cover all past, present, and future claims.
- Confidentiality must be explicit and include a duration.
- Governing law must specify the state court jurisdiction.
- "Time is of the essence" is always required.
- TONE: Formal legal language. Use "the Parties" and "the Agreement" throughout."""
            },

            # -----------------------------------------------------------------
            # ID 3 — SUBCONTRACTOR CONSTRUCTION SERVICES AGREEMENT
            # Based on: Gocontract- Subcontratctor Construccion Services.docx
            # UI: Contractors Business Ops → Subcontractor Agreement
            # -----------------------------------------------------------------
            {
                "id": 3,
                "category": "construction",
                "title": "Subcontractor Agreement",
                "description": "Contrato para subcontratistas en proyectos de construcción. Incluye pay-if-paid, OSHA, seguros, garantías y retención de pagos.",
                "rules": """GENERATE A "SUBCONTRACTOR CONSTRUCTION SERVICES AGREEMENT" WITH EXACTLY THIS STRUCTURE:

TITLE: "SUBCONTRACTOR CONSTRUCTION SERVICES AGREEMENT"

HEADER BLOCK:
This Subcontractor Construction Services Agreement ("Agreement") is entered into on [agreementDate] between:

Contractor:
[clientName]
[clientAddress]

Subcontractor:
[contractorName]
[contractorAddress]

SECTION 1 — Parties:
Identify Contractor ([clientName], [clientAddress]) and Subcontractor ([contractorName], [contractorAddress]).

SECTION 2 — Scope of Work:
The Subcontractor shall provide all labor, supervision, materials, tools, and equipment necessary to perform the following work:
[scopeOfWork]
All work must comply with project plans, building codes, OSHA standards, and all federal, state, and local laws.
Project Name: [projectName]
Project Location: [projectLocation]
Start Date: [projectStartDate]
Completion Date: [projectCompletionDate]

SECTION 3 — Contract Price:
Total: $[totalContractPrice]
Payment Structure:
- Deposit: $[depositAmount]
- [paymentSchedule] (Progress Payments / Milestone-based)
- Final Payment upon completion and inspection approval

SECTION 4 — Pay-If-Paid Clause:
[If payIfPaidClause:] Payment to Subcontractor is EXPRESSLY CONDITIONED upon payment received from the Project Owner. Contractor shall have NO OBLIGATION to pay Subcontractor until Contractor receives payment for the Subcontractor's work.

SECTION 5 — Schedule and Performance:
Start Date: [projectStartDate]
Completion Date: [projectCompletionDate]
TIME IS OF THE ESSENCE. Delays caused by Subcontractor may result in damages.

SECTION 6 — Liquidated Damages:
[If liquidatedDamages is provided:] If the Subcontractor causes delays in project completion, the Subcontractor agrees to pay $[liquidatedDamages] per day until completion of the work.

SECTION 7 — Insurance Requirements:
Subcontractor shall maintain:
- General Liability: [generalLiabilityMin]
[If workersCompRequired:] - Workers Compensation: As required by law
[If autoLiabilityRequired:] - Commercial Auto Liability: $1,000,000
[If additionalInsuredRequired:] Contractor must be listed as Additional Insured on all policies.

SECTION 8 — Safety Compliance:
[If oshaComplianceRequired:] Subcontractor must comply with OSHA regulations, jobsite safety policies, and all applicable safety laws. Subcontractor is responsible for the safety of its employees and sub-subcontractors.

SECTION 9 — Warranty of Work:
Subcontractor warrants that all work will be performed in a professional and workmanlike manner.
Warranty period: [warrantyPeriod] from project completion.

SECTION 10 — Backcharge Clause:
[If backchargeClause:] Contractor may charge Subcontractor for costs related to:
- Defective work
- Cleanup
- Damage to property
- Failure to follow schedule
These costs may be deducted from payments owed to Subcontractor.

SECTION 11 — Indemnification:
[If subIndemnification:] Subcontractor agrees to defend, indemnify, and hold harmless Contractor and Owner from all claims arising from negligence, injury, property damage, or violation of law by Subcontractor.

SECTION 12 — Mechanic's Lien Waivers:
[If mechanicLienWaivers:] Subcontractor must provide conditional lien waivers with each payment request and a final unconditional lien waiver upon receipt of final payment.

SECTION 13 — Independent Contractor:
Subcontractor is an INDEPENDENT CONTRACTOR and solely responsible for taxes, labor compliance, and employee compensation. No employer-employee relationship exists between Contractor and Subcontractor.

SECTION 14 — Confidentiality:
[If subConfidentiality:] Subcontractor shall not disclose project plans, business information, or pricing to any third party without prior written consent from Contractor.

SECTION 15 — Termination:
Contractor may terminate this Agreement if Subcontractor:
- Fails to perform work per specifications
- Violates safety rules or OSHA standards
- Causes unreasonable delays
- Breaches any material term of this Agreement

SECTION 16 — Force Majeure:
[If forceMajeure:] Neither party shall be liable for delays caused by natural disasters, government actions, labor strikes, or events beyond reasonable control.

SECTION 17 — Dispute Resolution:
Disputes shall be resolved through negotiation, then mediation, and if necessary binding arbitration in the State of [governingLaw].

SECTION 18 — Governing Law:
This Agreement shall be governed by the laws of the State of [governingLaw].

SECTION 19 — Entire Agreement:
This Agreement represents the entire agreement between the Parties and supersedes all previous agreements or discussions.

SIGNATURE BLOCK:
Contractor
Name: [clientName]
Signature: _______________________
Title: ___________________________
Date: ___________________________

Subcontractor
Name: [contractorName]
Signature: _______________________
Title: ___________________________
Date: ___________________________

MANDATORY RULES:
- OSHA compliance reference MUST always appear regardless of form toggle.
- Insurance requirements with minimums MUST be specified.
- Pay-if-paid clause when payIfPaidClause is selected.
- Independent Contractor status (NOT employee) MUST be stated.
- Warranty period for workmanship MUST appear.
- JURISDICTION: State per governingLaw input. US federal OSHA standards always apply."""
            },

            # -----------------------------------------------------------------
            # ID 4 — INFLUENCER MARKETING AGREEMENT
            # Based on: Gocontract- Influencer Marketing Agreement .docx
            # UI: Brand, Content Marketing → Influencer Agreement / Content Creation
            # -----------------------------------------------------------------
            {
                "id": 4,
                "category": "brand",
                "title": "Influencer Agreement",
                "description": "Contrato para campañas de marketing con influencers y creadores de contenido. Incluye FTC compliance, derechos de imagen y cláusula de moralidad.",
                "rules": """GENERATE AN "INFLUENCER MARKETING AGREEMENT" WITH EXACTLY THIS STRUCTURE:

TITLE: "INFLUENCER MARKETING AGREEMENT"

HEADER BLOCK:
This Influencer Marketing Agreement ("Agreement") is entered into on [agreementDate], by and between:

Brand / Client
[clientName]
[clientAddress]

Influencer / Content Creator
[contractorName]
[contractorAddress]

Collectively referred to as the "Parties."

SECTION 1 — Purpose of Agreement:
The purpose of this Agreement is to establish the terms under which the Influencer will promote the Brand's products or services through sponsored content on social media platforms.

SECTION 2 — Scope of Sponsored Content:
The Influencer agrees to create and publish promotional content including:
[List selectedContentTypes — e.g., Sponsored posts, Short-form videos (Reels/TikTok/Shorts), Stories, Product Mentions, Live Appearances, Unboxing Videos]
Platforms: [list each platform from selectedPlatforms]
Deliverables:
- [sponsoredPostsCount] sponsored posts
- [storiesCount] stories
- [videosCount] videos
Content must follow brand guidelines provided by the Brand.

SECTION 3 — Content Approval:
The Brand shall have the right to review and approve content PRIOR to publication.
The Brand must respond within [brandApprovalWindow] business days.
If no response is received within that time, the content may be considered approved by default.
The Brand may request up to [revisionRoundsAllowed] round(s) of reasonable revisions.

SECTION 4 — Campaign Timeline:
Campaign Start Date: [campaignStartDate]
Campaign End Date: [campaignEndDate]
The Influencer agrees to publish content according to the agreed campaign schedule.

SECTION 5 — Compensation:
Total Compensation: $[compensationAmount] [currency]
Payment structure:
- Deposit: [depositAmount or "initial payment"] upon signing
- Final payment: upon completion of all deliverables
Payments shall be made within [paymentDue].

SECTION 6 — Exclusivity:
During the campaign period plus [exclusivityWindow] days before and after, the Influencer agrees NOT to promote competing products or brands within the same category unless authorized in writing by the Brand.

SECTION 7 — FTC Compliance and Advertising Disclosure (MANDATORY):
The Influencer MUST comply with all applicable advertising regulations, including disclosure requirements established by the Federal Trade Commission (FTC).
Sponsored content MUST clearly disclose its promotional nature using:
- #Ad
- #Sponsored
- #PaidPartnership
Failure to comply with disclosure requirements may result in removal of content and IMMEDIATE TERMINATION of this Agreement.

SECTION 8 — Intellectual Property Rights:
[Based on intellectualProperty:]
- If "Influencer retains ownership": The Influencer retains ownership of original creative content. The Brand receives a NON-EXCLUSIVE LICENSE to use the content for marketing, advertising, social media, and promotional purposes.
- If "Work for Hire" / client owns all: All content created under this Agreement is considered work made for hire and all rights vest in the Brand.
- If shared: Joint ownership with terms specified.
License duration: [contractDuration or agreed period].

SECTION 9 — Image and Likeness Rights:
[If imageLikeness:] The Influencer grants the Brand the right to use the Influencer's name, image, likeness, and voice solely for promotional purposes related to this campaign. Such usage must not misrepresent the Influencer or imply endorsement beyond the scope of this Agreement.

SECTION 10 — Influencer Representations:
The Influencer represents that:
- all content will be original and will not infringe third-party rights
- the Influencer has the legal right to publish all content
- the content will comply with all platform policies

SECTION 11 — Brand Responsibilities:
The Brand agrees to:
- provide accurate product information and brand guidelines
- deliver products or materials needed for the campaign in a timely manner
- respond to content approval requests within the agreed timeframe

SECTION 12 — Morals Clause (MANDATORY — ALWAYS INCLUDE):
The Brand may IMMEDIATELY TERMINATE this Agreement if the Influencer engages in conduct that could reasonably damage the Brand's reputation, including but not limited to:
- illegal activities
- offensive or discriminatory public behavior
- fraudulent promotion practices
- material misrepresentation

SECTION 13 — Confidentiality:
[If confidentiality:] Both Parties agree to keep confidential any business information disclosed during the campaign, including marketing strategies, financial terms, and campaign performance data.

SECTION 14 — Termination:
Either Party may terminate this Agreement with written notice.
Immediate termination may occur for material breach, including FTC non-compliance or morals clause violations.
Upon termination, the Brand shall compensate for deliverables completed and accepted prior to termination.

SECTION 15 — Limitation of Liability:
Neither Party shall be liable for indirect, incidental, or consequential damages. Total liability shall not exceed the total compensation paid under this Agreement.

SECTION 16 — Force Majeure:
Neither Party shall be liable for delays caused by natural disasters, government actions, platform outages, or events beyond reasonable control.

SECTION 17 — Dispute Resolution:
Disputes shall first be resolved through good faith negotiation, then mediation, and if necessary binding arbitration in the State of [governingLawState].

SECTION 18 — Governing Law:
This Agreement shall be governed by the laws of the State of [governingLawState].

SECTION 19 — Entire Agreement:
This Agreement constitutes the entire agreement between the Parties and supersedes all prior negotiations.

SIGNATURE BLOCK:
Brand / Client
Name: [clientName]
Signature: _______________________
Date: ___________________________

Influencer / Content Creator
Name: [contractorName]
Signature: _______________________
Date: ___________________________

MANDATORY RULES:
- FTC Disclosure (Section 7) is NON-NEGOTIABLE and MUST appear with #Ad #Sponsored #PaidPartnership, regardless of form inputs.
- Morals Clause (Section 12) is NON-NEGOTIABLE and MUST always appear.
- Exclusivity window must always be specified.
- IP ownership must be clearly delineated.
- JURISDICTION: US Federal FTC advertising regulations always apply. State law per governingLawState."""
            },

            # -----------------------------------------------------------------
            # ID 5 — GENERAL DURABLE POWER OF ATTORNEY
            # Based on: general_durable_power_of_attorney_USA.docx
            # UI: Workforce Immigration → Attorney Authorization / Limited Power of Attorney
            # -----------------------------------------------------------------
            {
                "id": 5,
                "category": "immigration",
                "subcategory": "poa",
                "title": "Attorney Authorization / Limited Power of Attorney",
                "description": "Poder notarial general y duradero para que un Agente (Attorney-in-Fact) actúe en nombre del Poderdante. No se ve afectado por incapacidad posterior.",
                "rules": """GENERATE A "GENERAL DURABLE POWER OF ATTORNEY" WITH EXACTLY THIS STRUCTURE:

TITLE: "GENERAL DURABLE POWER OF ATTORNEY"

INTRODUCTION:
This General Durable Power of Attorney ("Power of Attorney") is executed on [agreementDate], by:
[clientName], [clientIdPassport if provided], residing at [clientAddress] (hereinafter referred to as the "Principal").

The Principal hereby appoints:
[contractorName], [serviceProviderIdPassport if provided], [contractorAddress], as their Attorney-in-Fact and lawful representative (hereinafter referred to as the "Agent").

SECTION 1 — Grant of General Authority:
The Principal hereby grants the Agent FULL AUTHORITY to act on their behalf in all matters related to the administration, management, and disposition of their property, assets, rights, and interests, with the same legal effect as if the Principal were personally present.

SECTION 2 — Authority Over Property:
The Agent shall have full authority to:
- buy, sell, lease, exchange, transfer, or otherwise dispose of real and personal property
- negotiate and execute contracts relating to property transactions
- sign deeds, agreements, and other documents necessary to complete such transactions
- mortgage, pledge, or encumber property when necessary

SECTION 3 — Authority to Manage Financial Affairs:
The Agent is authorized to manage financial matters on behalf of the Principal, including:
- collecting and receiving money owed to the Principal
- issuing receipts, settlements, or releases of payment
- negotiating payment terms
- managing financial assets

SECTION 4 — Banking Authority:
The Agent shall have authority to:
- open, manage, monitor, and close bank accounts
- deposit or withdraw funds
- endorse checks or financial instruments
- conduct banking transactions through any lawful means

SECTION 5 — Authority to Enter Contracts:
The Agent may enter into and execute contracts on behalf of the Principal, including:
- lease agreements
- service agreements
- commercial contracts
- financial arrangements

SECTION 6 — Authority Before Public or Private Institutions:
The Agent may represent the Principal before government authorities, municipal institutions, tax authorities, utility providers, and private entities for administrative or legal procedures.

SECTION 7 — General Administrative Authority:
The Agent may perform any act necessary to manage, protect, or administer the Principal's assets and rights. The powers granted herein are illustrative and not exhaustive.

SECTION 8 — Durable Power of Attorney (MANDATORY):
THIS POWER OF ATTORNEY SHALL BE DURABLE and shall NOT be affected by the subsequent disability or incapacity of the Principal, to the extent permitted by applicable law. This instrument is executed as a Durable Power of Attorney under the laws of the State of [immigrationGoverningState].

SECTION 9 — Revocation:
This Power of Attorney shall remain in full force and effect unless revoked IN WRITING by the Principal. Revocation shall not affect acts taken by the Agent before receipt of written notice of revocation.

SECTION 10 — Governing Law:
This Power of Attorney shall be governed by the laws of the State of [immigrationGoverningState], United States of America.

SECTION 11 — Third-Party Reliance:
Any third party may rely upon the validity of this Power of Attorney and any actions taken pursuant to it until written notice of revocation is received by that third party.

NOTARY ACKNOWLEDGMENT BLOCK (ALWAYS INCLUDE):
State of [immigrationGoverningState]
County of ___________________
Before me, the undersigned Notary Public, personally appeared the above-named individual(s) who acknowledged executing this Power of Attorney for the purposes stated herein.

Notary Public Signature: __________________
My Commission Expires: __________________

SIGNATURE BLOCK:
Principal
Name: [clientName]
Signature: _______________________
Date: ___________________________

Agent (Attorney-in-Fact)
Name: [contractorName]
Signature: _______________________
Date: ___________________________

MANDATORY RULES:
- The "Durable" clause (Section 8) is NON-NEGOTIABLE — must state explicitly that the POA survives incapacity.
- Notary Acknowledgment block MUST always be included at the end.
- The Agent's authority must be listed with specific enumerated powers.
- Revocation must be "in writing" to be effective.
- JURISDICTION: State law per immigrationGoverningState. US law applies."""
            },

            # -----------------------------------------------------------------
            # ID 6 — INDEPENDENT CONTRACTOR AGREEMENT
            # Based on: Independent Contractor Agreement-Contractors Business Ops .docx
            # UI: Contractors Business Ops → Independent Contractor Agreement
            # -----------------------------------------------------------------
            {
                "id": 6,
                "category": "contractors",
                "subcategory": "general",
                "title": "Independent Contractor Agreement",
                "description": "Contrato completo para contratistas independientes. Incluye alcance de servicios, compensación, propiedad intelectual, no-exclusividad y status de contratista independiente.",
                "rules": """GENERATE AN "INDEPENDENT CONTRACTOR AGREEMENT" WITH EXACTLY THIS STRUCTURE:

TITLE: "INDEPENDENT CONTRACTOR AGREEMENT"

HEADER BLOCK:
THIS INDEPENDENT CONTRACTOR AGREEMENT (the "Agreement") is dated this [agreementDate].

CLIENT
[clientName]
[clientAddress]
(the "Client")

CONTRACTOR
[contractorName]
[contractorAddress]
(the "Contractor")

BACKGROUND:
A. The Client is of the opinion that the Contractor has the necessary qualifications, experience and abilities to provide services to the Client.
B. The Contractor is agreeable to providing such services to the Client on the terms and conditions set out in this Agreement.

IN CONSIDERATION OF the matters described above and of the mutual benefits and obligations set forth in this Agreement, the receipt and sufficiency of which consideration is hereby acknowledged, the Client and the Contractor agree as follows:

SERVICES PROVIDED:
1. The Client hereby agrees to engage the Contractor to provide the Client with the following services (the "Services"):
[List each service from servicesDescription as bullet points]
2. The Services will also include any other tasks which the Parties may agree on in writing. The Contractor hereby agrees to provide such Services to the Client.

TERM OF AGREEMENT:
3. The term of this Agreement (the "Term") will begin on [agreementDate] and will remain in full force and effect until the completion of the Services, subject to earlier termination as provided in this Agreement.
[If durationModel is fixedDuration:] The Term shall be [contractDurationValue] [contractDurationUnit].
[If durationModel is autoRenewal:] This Agreement shall automatically renew for successive [renewalFrequency] periods unless either Party provides [cancellationNotice] written notice of non-renewal.
The Term may be extended with the written consent of both Parties.

PERFORMANCE:
4. The Parties agree to do everything necessary to ensure that the terms of this Agreement take effect.

CURRENCY:
5. Except as otherwise provided in this Agreement, all monetary amounts referred to in this Agreement are in [currency] ([currency] Dollars/currency).

COMPENSATION:
6. [Based on compensationModel:]
- flatFee: The Contractor will charge the Client a flat fee of $[compensationAmount] [currency] for the Services (the "Compensation").
- hourlyRate: The Contractor will charge the Client at an hourly rate of $[compensationAmount] [currency] per hour.
- milestonePayments: The Contractor will be compensated on a milestone basis as specified: [list milestones with amounts]
- retainer: The Contractor will charge the Client a monthly retainer of $[compensationAmount] [currency].
7. The Client will be invoiced [invoiceTiming — upon completion / monthly / per milestone].
8. Invoices submitted by the Contractor to the Client are due within [paymentDue] of receipt.
9. [If earlyTermination:] In the event that this Agreement is terminated by the Client prior to completion of the Services but where the Services have been partially performed, the Contractor will be entitled to pro rata payment of the Compensation to the date of termination, provided that there has been no breach of contract on the part of the Contractor.
10. [If salesTaxIncluded is false:] The Compensation as stated in this Agreement does not include sales tax or other applicable duties as may be required by law.

REIMBURSEMENT OF EXPENSES:
11. The Contractor will be reimbursed for reasonable and necessary expenses incurred in connection with providing the Services.
12. All expenses must be pre-approved in writing by the Client.

INTEREST ON LATE PAYMENTS:
13. Interest payable on any overdue amounts under this Agreement is charged at a rate of [lateInterest] or at the maximum rate enforceable under applicable legislation, whichever is lower.

CONFIDENTIALITY:
14. "Confidential Information" refers to any data or information relating to the business of the Client which would reasonably be considered proprietary, including accounting records, business processes, and client records, that is not generally known in the industry.
15. The Contractor agrees not to disclose, divulge, reveal, report or use any Confidential Information for any purpose except as authorized by the Client or as required by law. Confidentiality obligations apply [based on confidentialityDuration: during term only / term + 2 years / indefinitely for trade secrets / custom duration].

OWNERSHIP OF INTELLECTUAL PROPERTY:
16. [Based on ipOwnership:]
- workForHire: All intellectual property, work product, and related material developed under this Agreement is a "WORK MADE FOR HIRE" and will be the SOLE PROPERTY OF THE CLIENT. The use of the Intellectual Property by the Client will not be restricted in any manner.
- exclusiveLicense: The Client receives an exclusive license to use all work product developed under this Agreement.
- nonExclusiveLicense: The Contractor retains ownership; the Client receives a non-exclusive license.
- shared: Joint ownership with equal rights unless otherwise agreed.
17. The Contractor may not use the Intellectual Property for any purpose other than that contracted for in this Agreement except with written consent of the Client.

RETURN OF PROPERTY:
18. Upon the expiration or termination of this Agreement, the Contractor will return to the Client any property, documentation, records, or Confidential Information which is the property of the Client.

CAPACITY / INDEPENDENT CONTRACTOR (MANDATORY):
19. In providing the Services under this Agreement it is EXPRESSLY AGREED that the Contractor is acting as an INDEPENDENT CONTRACTOR and NOT as an employee. This Agreement does NOT create a partnership or joint venture. The Client is NOT required to pay, or make any contributions to, any social security, federal or state tax, unemployment compensation, workers' compensation, insurance premium, profit-sharing, pension or any other employee benefit for the Contractor. The Contractor is responsible for paying and complying with all reporting requirements for taxes related to payments made under this Agreement.

RIGHT OF SUBSTITUTION:
20. [Based on subcontracting:]
- allowedWithApproval: The Contractor may engage sub-contractors to perform obligations under this Agreement with prior written approval from the Client.
- allowedWithoutApproval: The Contractor may engage sub-contractors to perform some or all obligations under this Agreement.
- notAllowed: The Contractor shall not sub-contract any obligations under this Agreement without the Client's prior written consent.

AUTONOMY:
21. Except as otherwise provided in this Agreement, the Contractor will have full control over working time, methods, and decision making in relation to provision of the Services. The Contractor will be responsive to the reasonable needs and concerns of the Client.

EQUIPMENT:
22. Except as otherwise provided in this Agreement, the Contractor will provide at the Contractor's own expense any and all tools, equipment, and materials necessary to deliver the Services.

NO EXCLUSIVITY:
[If nonExclusivity:] 23. The Parties acknowledge that this Agreement is non-exclusive and that either Party will be free, during and after the Term, to engage or contract with third parties for the provision of services similar to the Services.

NOTICE:
24. All notices required by the terms of this Agreement will be given in writing and delivered to the Parties at:
a. [clientName], [clientAddress]
b. [contractorName], [contractorAddress]

INDEMNIFICATION:
25. [Based on indemnification:]
- standardMutual: Each Party agrees to indemnify and hold harmless the other Party, its directors, officers, agents, and employees from claims arising from the indemnifying party's acts or omissions in connection with this Agreement.
- oneSided: The Contractor agrees to indemnify and hold harmless the Client from claims arising from the Contractor's performance of Services.

MODIFICATION:
26. Any amendment or modification of this Agreement will only be binding if evidenced in writing signed by each Party.

TIME OF THE ESSENCE:
27. Time is of the essence in this Agreement. No extension or variation of this Agreement will operate as a waiver of this provision.

GOVERNING LAW:
28. This Agreement will be governed by and construed in accordance with the laws of the State of [governingLaw].

SEVERABILITY:
[If includeSeverability:] 29. In the event that any provisions of this Agreement are held to be invalid or unenforceable, all other provisions will continue to be valid and enforceable.

ENTIRE AGREEMENT:
30. It is agreed that there is no representation, warranty, collateral agreement or condition affecting this Agreement except as expressly provided in this Agreement.

SIGNATURE BLOCK:
[clientName] (Client)
Signature: _______________________
Date: ___________________________

[contractorName] (Contractor)
Signature: _______________________
Date: ___________________________

MANDATORY RULES:
- Independent Contractor status (NOT employee) — Section 19 MUST appear verbatim. This is legally critical.
- Intellectual Property / Work for Hire clause MUST appear.
- Late payment interest clause MUST appear.
- Time is of the essence MUST appear.
- JURISDICTION: State per governingLaw input."""
            },

            # -----------------------------------------------------------------
            # ID 7 — SOCIAL MEDIA MANAGEMENT / MARKETING SERVICES AGREEMENT
            # Based on: Social Media Management Service Agreement-Brand, Content Marketing.docx
            # UI: Brand, Content Marketing → Marketing Services Agreement
            #     Also maps to: Advertising Management Agreement, Content Creation & Licensing Agreement
            # -----------------------------------------------------------------
            {
                "id": 7,
                "category": "brand",
                "subcategory": "marketing",
                "title": "Marketing Services Agreement",
                "description": "Acuerdo de gestión de redes sociales y producción de contenido. Incluye fases de proyecto, términos de pago, propiedad intelectual y política de cancelación.",
                "rules": """GENERATE A "SOCIAL MEDIA MANAGEMENT SERVICE AGREEMENT" as a complete, professional legal document. Use the input data below to fill in all specifics. The contract must cover the following topics and information (use this as a content reference, NOT as literal text to copy):

CONTENT THAT MUST BE INCLUDED:

1. PURPOSE AND SCOPE OF SERVICES:
- Services provided: [msaServices] (list all selected services)
- Total content pieces: [msaContentCount] per month ([msaVideosCount] videos and [msaStaticPostsCount] static posts)
- Platforms where content will be published: [selectedPlatforms]
- Include: monitoring & responding to messages, engagement strategy & lead generation, advertising campaign management on selected platforms, monthly performance report.

2. PROJECT STAGES (always include all 4 in this order):
- Quotation Stage: pre-signing activities, no work begins until deposit received.
- Strategy Development Stage: starts 1 business day after deposit, research + creative strategy, ends upon client approval.
- Design/Recording Stage: content creation and production, up to [msaRevisionRounds] revision rounds, ends upon written client approval.
- Launching Stage: final delivery and publishing, additional charges apply for post-approval changes.

3. TERM AND RENEWAL:
- Duration: [contractDuration]
- Renewal type: [renewalTerm] (No Renewal = new agreement required; Auto Renewal = auto-renews if no written cancellation 1 month prior; Manual Renewal = explicit agreement needed)

4. OBLIGATIONS OF BOTH PARTIES:
- Provider: deliver services per best practices, monthly reports, manage ad budgets, maintain confidentiality.
- Client: provide materials, make timely payments, approve content within deadlines.

5. TIMELINE AND SCHEDULE:
- Schedule shared via Google Calendar.
- Changes require 7 days advance notice.
- Unauthorized schedule changes incur a 5% fee.
- Cancellation within 2 business days of deposit: 50% refund. After that: no refund.
- Formal cancellation via official email only.

6. FEES AND PAYMENT TERMS:
- Monthly service fee: $[msaMonthlyFee] USD
- [If msaAdvertisingBudget is true: include that it covers a social media advertising budget]
- Late payment penalty: [msaLatePaymentFee], max 50% of outstanding amount.
- Services suspended if payment not received within 15 calendar days.
- Unauthorized content use before full payment = breach of contract.
- Accepted payment methods (mark selected ones): Bank Transfer / Check / Cash / Credit Card (credit card includes 2.99% processing fee)
  Accepted: [msaPaymentMethods]

7. FEES AND PENALTIES:
- No refund after cancellation post-advance-payment.
- Termination requires formal written communication.

8. INTELLECTUAL PROPERTY:
- All materials belong to The Agency until full payment.
- Upon full payment: client receives limited, non-exclusive, non-transferable license.
- Client cannot resell, sublicense, or modify without written authorization.
- Client warrants ownership of any provided content/logos.
- [If msaPortfolioRights is true:] Agency retains right to use work for portfolio/promotional purposes.

9. MODIFICATIONS AND SERVICE CHANGES:
- [msaRevisionRounds] revision rounds per deliverable; additional revisions billed at hourly rate.
- Client must approve deliverables in writing.
- No response within [msaImpliedApproval] = implied acceptance / auto-approval.
- Post-approval modifications require new quotation.

10. CONFIDENTIALITY AND PROFESSIONAL RELATIONSHIP:
- Confidential information safeguarded indefinitely.
- [If msaNDA is true:] NDA included as annex.
- [If msaNonCompete is true:] Non-Compete Agreement included as annex.
- [If msaPortfolioRights is true:] Provider may use work for portfolio after delivery.
- Professional conduct required; no defamation. Breach = legal action.

11. LIMITATION OF LIABILITY:
- Not liable for: platform algorithm changes, client misuse, third-party losses, expected outcomes (sales/leads/engagement).
- Liability capped at total fees paid under this Agreement.

12. INDEPENDENT CONTRACTOR STATUS:
- Provider is independent contractor. No partnership, employment, or joint venture created.

13. NON-SOLICITATION:
- [If msaNonSolicitation is true:] Client may not hire/solicit Agency staff for [msaNonSolicitationDuration] months after termination.

14. TERMINATION AND CANCELLATION POLICY:
- Refund policy: [msaRefundPolicy]
- No refunds after the applicable period.
- Work completed to termination date billed in full.
- Written cancellation via email to signing representative required.

15. JURISDICTION AND DISPUTE RESOLUTION:
- Governed by laws of State of [msaJurisdiction].
- Disputes resolved in courts of [msaJurisdiction].

SIGNATURE BLOCK:
- The Agency: Name [clientName], Signature line, Phone, Date
- The Client: Name [contractorName], Signature line, Phone, Date

MANDATORY RULES:
- Write in formal, professional legal English.
- All 4 project stages MUST appear in Section 2.
- NO WORK STARTS before deposit is received — state this clearly.
- Revision rounds = [msaRevisionRounds]. Implied acceptance after [msaImpliedApproval].
- Non-solicitation duration = [msaNonSolicitationDuration] months (if enabled).
- Jurisdiction = [msaJurisdiction].
- Include NDA/Non-Compete mentions only if msaNDA/msaNonCompete are true."""
            },

            # -----------------------------------------------------------------
            # ID 8 — MAINTENANCE AGREEMENT
            # Based on: Maintenance Agreement -Contractors Business Ops.pdf
            # UI: Contractors Business Ops → Maintenance Agreement
            # -----------------------------------------------------------------
            {
                "id": 8,
                "category": "contractors",
                "subcategory": "services",
                "title": "Maintenance Agreement",
                "description": "Acuerdo de mantenimiento profesional entre un proveedor de servicios y un cliente. Cubre alcance, frecuencia, pagos, confidencialidad, responsabilidad y resolución de disputas.",
                "rules": """You are generating a professional MAINTENANCE AGREEMENT. Use the form data provided to populate all fields. Write in formal legal English.

CONTEXT (use as reference for the type of content and clauses to include — do NOT copy verbatim):
A maintenance agreement typically covers: the identity of both parties (service provider and client), the specific services to be performed and their frequency, response time commitments, fee structure and payment schedule, contract duration and renewal terms, client obligations (access, notification of issues, clearing obstructions), exclusions and limitations of warranty, liability cap, confidentiality obligations, force majeure / act of God exclusions, termination conditions and notice period, dispute resolution method, and governing law. The agreement should be clear, professional, and enforceable.

FORM DATA TO USE:
- Service Provider: [maintServiceProviderName], [maintServiceProviderAddress], Email: [maintServiceProviderEmail]
- Client: [maintClientName], [maintClientAddress], Email: [maintClientEmail]
- Service Type: [maintServiceType]
- Service Description: [maintServiceDescription]
- Equipment / Areas Covered: [maintEquipmentAreas]
- Maintenance Frequency: [maintFrequency]
- Response Time Commitment: [maintResponseTime]
- Payment Amount: $[maintPaymentAmount]
- Billing Frequency: [maintBillingFrequency]
- Payment Method: [maintPaymentMethod]
- Late Payment Fee: [maintLatePaymentFee]
- Reimbursable Expenses: [maintReimbursable]
- Start Date: [maintStartDate]
- Contract Duration: [maintContractDuration]
- Automatic Renewal: [maintAutoRenewal]
- Termination Notice Period: [maintTerminationNotice]
- Termination Conditions: [maintTerminationConditions]
- Confidentiality (NDA): [maintNDA] — Period: [maintConfidentialityPeriod]
- Liability Limitation: [maintLiabilityLimit] (custom amount if applicable: $[maintCustomLiabilityAmount])
- Professional Liability Insurance Required: [maintProfessionalInsurance] — Min Coverage: $[maintMinCoverage]
- Governing Law: State of [maintGoverningLaw]
- Dispute Resolution: [maintDisputeResolution]

MANDATORY CLAUSES TO ALWAYS INCLUDE:
1. Clear identification of both parties with full name, address, and email.
2. Detailed scope of services, equipment/areas covered, and service frequency.
3. Response time commitment for service calls.
4. Payment terms including amount, billing frequency, method, and late payment consequences.
5. Contract duration, start date, auto-renewal terms (if applicable), and termination notice requirements.
6. Immediate termination conditions (include the selected ones from maintTerminationConditions).
7. Client obligations: must notify provider of defects/issues promptly, provide access, clear obstructions, pay on time.
8. Force majeure / Act of God exclusion — provider not liable for floods, earthquakes, hurricanes, or other extraordinary events.
9. Limitation of liability — provider's liability capped per maintLiabilityLimit selection.
10. Warranty limitation — work by unauthorized third parties voids this agreement.
11. Confidentiality section if maintNDA is true, covering the information types listed and lasting [maintConfidentialityPeriod] after contract ends.
12. Professional liability insurance requirement if maintProfessionalInsurance is true.
13. Dispute resolution method per [maintDisputeResolution].
14. Governing law: State of [maintGoverningLaw].
15. Entire agreement clause.
16. Signature block for both parties (Service Provider and Client), with Name, Signature, and Date lines.

GENERATE THE CONTRACT NOW using professional legal language. Structure it with numbered sections. Do not include placeholder brackets in the final output — replace all variables with the actual values from the form data."""
            },

            # -----------------------------------------------------------------
            # ID 9 — LEGAL SERVICE AGREEMENT
            # Based on: IACONA LAW, PLLC - Legal Services Agreement template
            # UI: Workforce & Immigration → Legal Service Agreement
            # -----------------------------------------------------------------
            {
                "id": 9,
                "category": "immigration",
                "subcategory": "legal_services",
                "title": "Legal Service Agreement",
                "description": "Acuerdo de servicios legales de inmigración entre una firma de abogados y el cliente. Cubre alcance del caso, honorarios, facturación, terminación, comunicación, privacidad y arbitraje.",
                "rules": """You are generating a professional LEGAL SERVICES AGREEMENT for an immigration law firm. Use the form data provided to populate all fields. Write in formal legal English following the exact structure below.

CONTEXT — Use this as your content and clause reference (this mirrors a real immigration law firm's engagement letter):
This is a binding attorney-client engagement letter that outlines the scope of representation for an immigration matter, the fee structure, billing terms, late payment consequences, termination rights, document retention, communication standards, arbitration clause, privacy policy, attorney-client privilege, and entire agreement clause.

DOCUMENT STRUCTURE — Generate the contract with EXACTLY these sections:

HEADER:
- Title: LEGAL SERVICES AGREEMENT (bold, centered)
- "Dear [clientName]"
- "Re: Engagement for Legal Services"
- Opening paragraph: "Thank you for choosing [contractorName] ("the Firm") to represent you on your immigration matter. The purpose of this engagement letter ("Agreement") is to outline the nature of the engagement and our respective responsibilities and expectations under this Agreement."

1. SCOPE OF THE ENGAGEMENT:
- State that representation is limited to: [lsCaseTypes joined as list]
- Explicitly state it does NOT include: any other actual or potential litigation, appeals, arrangements, motions, interview appearances, court reviews, dealing with deportation or exclusion grounds or proceedings, extensions of nonimmigrant visas and other services.
- Also exclude the following services specifically selected: [lsExcludedServices]
- [If lsAdjustmentOfStatus is true: "Adjustment of Status, either concurrent or separate in any future time, are not part of the legal fee, it will have an additional fee to be discussed with our Firm at the time at which you will chose to file for it."]
- [If lsConsularProcessing is true: "Consular Processing is not part or included in this agreement."]
- State that work will be performed by [contractorName], Lead Attorney. Representation may be expanded if the parties separately agree in writing.
- After the engagement concludes with a final decision from USCIS, the Firm has no further obligation to advise.
- Add a paragraph about the Firm doing its best but not guaranteeing outcomes due to USCIS discretionary power. End with: "Therefore, we have not made, and cannot make, any guarantees or promises concerning the outcome of this matter."
- Add scope description if provided: [lsScopeDescription]

2. FEES:
- "The legal fee applicable to this engagement will correspond to the service package and payment option selected by the Client."
- Total Engagement Fee: $[lsTotalEngagementFee]
- Payment Plan selected: [lsPaymentPlan]
- [If lsSpanishTranslations: "This legal fee includes translations from Spanish to English of those documents required to be submitted or recommended to be submitted with the case. Any additional translations of documents not in Spanish shall be billed separately to the Client."]
- [If lsNonRefundable: "It is expressly understood that this fixed engagement fee is based upon the scope of engagement as defined above. And that all fixed fee payments received are non-refundable and earned upon receipt."]
- [If lsGovFilingFeesSeparate: "In addition to our basic fixed legal fee, we will be entitled to advance payment or reimbursement for costs and expenses incurred in performing services, such as government filing fees that are required by USCIS to handle this petition."]
- Add paragraph about timely document submission being essential; delays by Client may incur additional fees.

3. BILLING:
- "For your convenience, we have extended a payment plan for the client to pay the engagement fee which was due and owed the day of the signing of this legal services agreement."
- "Payment is due according with the payment schedule described above."
- Add in bold/italic: "Filings will not be made until our invoice has been paid according with the payment schedule, so be certain to send the fees to us prior to your desired filing date."

4. LATE PAYMENTS:
- "Any payment not received within [lsGracePeriodDays] days from the due date stated on the invoice will incur a late fee of $[lsLateFeeAmount]."
- "This late fee will be charged for each month the payment remains outstanding, with an additional $[lsLateFeeAmount] fee accumulating for every subsequent month of non-payment until the full balance is settled."

5. TERMINATION OF THE REPRESENTATION:
- [If lsClientMayTerminate: "You shall have the right at any time to terminate our services and representation under this Agreement, upon written notice to the Firm."]
- [If lsFullFeesOwed: "Such termination, however, shall not relieve you of the obligation to pay the full engagement fee which was due and owed the day of the signing of this legal services Agreement. Please note that this might include fees for services rendered, even if not completed, translations, letter drafting and any other legal services or expenses related to your matter. Any payments that you have made already towards your case will NOT be refunded."]
- [If lsFirmMayTerminate: "We also have the right to terminate the representation for good cause. Good cause to withdraw includes, but is not limited to: (a) your failure to honor the terms of the engagement, (b) your failure to cooperate or follow our advice on a material matter, (c) circumstances where our continued representation would be unlawful or unethical, or (d) any other reason permitted by the applicable ethics rules."]
- Add: In the event of firm termination, the firm will inform the Client in writing and take steps to protect Client's interests.

6. CLIENT DOCUMENTS:
- "During the engagement, we will maintain all documents relevant to this representation."
- "At the conclusion of this engagement, we will retain your record documents for a period of [lsDocumentRetentionYears] years unless you request that they be returned to you. If you have not requested possession of the file or any of its contents at the end of [lsDocumentRetentionYears] years, the file will be destroyed in accordance with our record retention program."

7. REASONABLE COMMUNICATION CLAUSE:
- [If lsReasonableCommunication: Include the full reasonable communication clause: "The Client agrees to maintain communication with the Firm that is purposeful, necessary, and directly related to the case's progression and legal strategy. Both case-related and non-case-related communications should be conducted with a focus on efficiency, relevance, and respect for the Attorney's responsibilities towards all clients and the legal practice. Therefore, the Client commits to engaging in communications that are deemed reasonable in frequency and nature by the Attorney. Should the Attorney determine that the volume or nature of communication becomes excessive, the Attorney reserves the right to request a modification in communication practices and, if necessary, to implement measures to ensure that communications remain constructive and within reasonable bounds."]
- [If lsRespectfulConduct: Include: "Respectful Communication and Conduct Clause: The Client hereby commits to uphold the highest standards of respect, professionalism, and courtesy in all forms of communication and interaction with the Attorney, as well as any staff, associates, or representatives of the law firm. Disrespectful conduct, abusive language, harassment, or any form of discrimination against the Attorney or any member of the law firm's staff will not be tolerated under any circumstances."]
- [If lsElectronicCommunication: Include: "Unless you specifically direct us otherwise, we may use mobile phones, email, and facsimile machines in the course of this engagement. Our email and facsimile transmissions may not be encrypted so the use of such forms of communication under current technologies may place confidential or privileged information at risk. By signing below, you consent to our use of these forms of communication."]

8. ADDITIONAL CLIENT RESPONSIBILITIES:
- Client agrees to communicate and provide complete, timely, and accurate information.
- Client will timely notify the Firm of any changes in personal information.
- Add: "Unreasonable delays in client sending complete information might generate re-processing, delays, and additional cost to the client."

9. TIME FRAME:
- "The estimated time frame for the preparation of your application will be determined according to the package selected by the client."
- Add in bold: "The time will start counting from the date on which ALL the documents and information required have been uploaded by the client to the assigned CLIENT PORTAL and received by our firm."

10. ARBITRATION:
- [If lsDisputeResolution is "Binding Arbitration (AAA)": "Client and Firm agree that any dispute, controversy, or claim arising out of, or relating to, this Agreement or the breach thereof shall be resolved by binding, final arbitration between the parties conducted in [lsArbitrationLocation if provided, else "Miami-Dade County, Florida"], in accordance with the rules of the American Arbitration Association ("AAA"). The award of the Arbitrator shall be conclusive and binding upon both parties and judgment upon the award may be entered in any court of competent jurisdiction."]
- [If lsDisputeResolution is "Mediation": "Any dispute arising under this Agreement shall be resolved through mediation before a mutually agreed mediator."]
- [If lsDisputeResolution is "Litigation": "Any dispute arising under this Agreement shall be subject to the exclusive jurisdiction of the courts of the State of [lsGoverningLaw]."]

11. PRIVACY:
- [If lsPrivacyClause: "In the course of providing legal services to you, we may receive nonpublic personal information about you. All such information will be held in strict confidence and will not be disseminated to any person or entity outside this Firm without your consent, unless such disclosure is required under the applicable law."]
- [If lsCloudStorageConsent: "We may store some or all of your files on a variety of platforms, including third-party cloud-based servers. Although we take every precaution to make sure these servers are encrypted and secure, there still is a risk that your confidential or privileged information may be disclosed. By signing below, you consent to our use of such storage services."]

12. ATTORNEY-CLIENT PRIVILEGE:
- [If lsAttorneyClientPrivilege: "Generally, information we receive from you is subject to the attorney-client privilege. However, we may be under an independent ethical duty to reveal privileged information if (a) it involves the commission of illegal or fraudulent acts that are committed during this engagement, (b) it involves the intent to commit a crime, or (c) we are required to disclose the information by law or court order."]

13. ENTIRE AGREEMENT:
- [If lsEntireAgreementClause: "This Agreement constitutes the sole and entire agreement between us with respect to the subject matter of this Agreement, and supersedes all prior and contemporaneous understandings, agreements, representations, and warranties, both written and oral, with respect to the subject matter."]
- Governing Law: This Agreement shall be governed by and construed in accordance with the laws of the State of [lsGoverningLaw].

CLOSING:
- "We appreciate the opportunity to be of service and look forward to working with you."
- "Very truly yours,"
- Signature block for Law Firm/Attorney: Name, Title, Firm name
- "ACCEPTED AND AGREED:"
- Signature block for Client: Name [clientName], Signature line, Date line

MANDATORY RULES:
- Replace ALL bracketed variables with actual form data values. Never leave placeholders.
- Use formal legal English throughout.
- Section headings should be bold and numbered.
- The document should read as a professional attorney engagement letter, not a generic contract template.
- Language: Respond in English unless inputs indicate Spanish."""
            },
        ]

        # UPSERT logic: insert if not exists, update rules if already exists
        for t_data in templates_data:
            result = await db.execute(select(TemplateContract).where(TemplateContract.id == t_data["id"]))
            existing = result.scalar_one_or_none()
            if not existing:
                template = TemplateContract(**t_data)
                db.add(template)
                print(f"Added template: {t_data['title']}")
            else:
                # Update rules, description, and category on existing templates
                existing.rules = t_data["rules"]
                existing.description = t_data["description"]
                existing.category = t_data["category"]
                if "subcategory" in t_data:
                    existing.subcategory = t_data.get("subcategory")
                existing.title = t_data["title"]
                db.add(existing)
                print(f"Updated template: {t_data['title']}")

        # =====================================================================
        # 3. Seed / Update Agents (one per template)
        # =====================================================================
        agents_data = [
            {
                "template_id": 1,
                "title": "Asistente de Formularios Migratorios",
                "prompt": """Eres un asistente experto en preparación de formularios de inmigración ante el USCIS.
IMPORTANTE: Debes dejar absolutamente claro al usuario que NO eres un abogado y NO provees asesoría legal.
Ayuda al usuario a identificar qué formularios necesita (I-130, I-485, I-765, I-589, I-131, I-140, I-864, N-400, I-751, I-90, etc.) y a completar los datos del acuerdo.
Recuerda siempre: los honorarios del gobierno (filing fees) son SEPARADOS de los honorarios del proveedor de servicios.
No hay NINGUNA garantía de aprobación — el USCIS toma las decisiones de forma independiente."""
            },
            {
                "template_id": 2,
                "title": "Mediador de Terminación de Contratos",
                "prompt": """Eres un experto en terminación de contratos y resolución de disputas.
Ayuda a redactar una terminación justa y mutuamente beneficiosa que proteja a ambas partes de litigios futuros.
Asegúrate de que se incluya: liberación mutua de todas las reclamaciones pasadas y futuras, confidencialidad post-terminación, y que no queden obligaciones pendientes sin resolver.
Verifica que el usuario entienda la diferencia entre terminación inmediata, en fecha específica y condicional."""
            },
            {
                "template_id": 3,
                "title": "Coordinador de Contratos de Construcción",
                "prompt": """Eres un gestor de proyectos de construcción con experiencia en contratos de subcontratistas.
Enfócate en: cumplimiento de normas OSHA, requisitos de seguro, cláusula pay-if-paid, calendario de pagos por hitos, y garantías de mano de obra.
Ayuda al usuario a definir claramente el alcance del trabajo, las penalidades por retraso (liquidated damages), y los requisitos de lien waivers (exención de gravámenes).
Recuerda: el subcontratista es un contratista INDEPENDIENTE, no un empleado."""
            },
            {
                "template_id": 4,
                "title": "Manager de Campañas con Influencers",
                "prompt": """Eres un experto en marketing digital y contratos con influencers y creadores de contenido.
Ayuda al usuario a definir: número exacto de deliverables (posts, stories, videos), ventana de exclusividad, proceso de aprobación de contenido, y cumplimiento de la FTC.
IMPORTANTE: Siempre recuerda que el contenido patrocinado debe llevar #Ad, #Sponsored o #PaidPartnership — esto es un requisito legal de la FTC, no opcional.
Verifica la cláusula de moralidad (morals clause) y la propiedad intelectual (quién retiene los derechos del contenido creado)."""
            },
            {
                "template_id": 5,
                "title": "Asistente de Poder Notarial",
                "prompt": """Eres un asistente experto en poderes notariales (Power of Attorney) bajo las leyes de Estados Unidos.
Ayuda al usuario a entender la diferencia entre un poder notarial general, limitado y durable.
IMPORTANTE: Este es un poder DURABLE, lo que significa que NO se ve afectado por la incapacidad posterior del Poderdante.
Asegúrate de que el usuario entienda que este documento requiere notarización para ser válido.
Recuerda especificar claramente los poderes que se otorgan al Agente (Attorney-in-Fact) y las condiciones de revocación."""
            },
            {
                "template_id": 6,
                "title": "Asistente de Contrato de Contratista Independiente",
                "prompt": """Eres un experto en contratos para contratistas independientes.
Ayuda al usuario a entender la diferencia CRÍTICA entre un contratista independiente y un empleado — esto tiene implicaciones tributarias y laborales importantes.
Asegúrate de incluir: alcance claro de servicios, modelo de compensación, propiedad intelectual (work for hire vs. licencia), no-exclusividad, y cláusula de no-solicitud de empleados.
Recuerda: el contratista independiente es responsable de sus propios impuestos, seguros y gastos operativos."""
            },
            {
                "template_id": 7,
                "title": "Manager de Servicios de Marketing Digital",
                "prompt": """Eres un experto en contratos de marketing digital y gestión de redes sociales.
Ayuda al usuario a definir claramente: plataformas, tipos de contenido, número de piezas, presupuesto de publicidad, y fases del proyecto.
IMPORTANTE: Ningún trabajo comienza hasta recibir el depósito inicial.
Recuerda las 4 fases del acuerdo: Cotización → Estrategia → Diseño/Grabación → Lanzamiento.
Asegúrate de que el cliente entienda la política de revisiones (máximo [X] rondas) y la política de cancelación (reembolso 50% en los primeros 2 días hábiles)."""
            },
            {
                "template_id": 8,
                "title": "Coordinador de Acuerdos de Servicio",
                "prompt": """Eres un experto en contratos de prestación de servicios y acuerdos de mantenimiento.
Ayuda al usuario a definir claramente: alcance de servicios, tarifa, duración del acuerdo, y obligaciones de ambas partes.
Recuerda que el proveedor de servicios NO es responsable por: cambios de algoritmos, mal uso del cliente, o resultados esperados (ventas, engagement).
Asegúrate de que el cliente entienda sus obligaciones: notificar defectos oportunamente, proveer acceso adecuado, y pagar a tiempo."""
            },
        ]

        for a_data in agents_data:
            result = await db.execute(select(Agent).where(Agent.template_id == a_data["template_id"]))
            existing_agent = result.scalar_one_or_none()
            if not existing_agent:
                agent = Agent(**a_data)
                db.add(agent)
                print(f"Added agent for template ID: {a_data['template_id']}")
            else:
                existing_agent.title = a_data["title"]
                existing_agent.prompt = a_data["prompt"]
                db.add(existing_agent)
                print(f"Updated agent for template ID: {a_data['template_id']}")

        await db.commit()
        print("Success: Database seeding completed with optimized contract templates.")

if __name__ == "__main__":
    asyncio.run(seed_data())
