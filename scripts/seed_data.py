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
        plans_data = [
            {
                "id": 1,
                "title": "Free",
                "description": "Prueba básica para redactar tus primeros contratos.",
                "price": 0.0,
                "contracts_included": 2,
                "time_subscription": "lifetime"
            },
            {
                "id": 2,
                "title": "Pro",
                "description": "Ideal para profesionales e independientes.",
                "price": 29.99,
                "contracts_included": 15,
                "time_subscription": "monthly"
            },
            {
                "id": 3,
                "title": "Enterprise",
                "description": "Contratos ilimitados para grandes empresas.",
                "price": 99.99,
                "contracts_included": 1000,
                "time_subscription": "monthly"
            }
        ]

        for p_data in plans_data:
            result = await db.execute(select(Plan).where(Plan.id == p_data["id"]))
            if not result.scalar_one_or_none():
                plan = Plan(**p_data)
                db.add(plan)
                print(f"Added plan: {p_data['title']}")

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
                "rules": """GENERATE A "SOCIAL MEDIA MANAGEMENT SERVICE AGREEMENT" OR "MARKETING SERVICES AGREEMENT" WITH EXACTLY THIS STRUCTURE:

TITLE: "SOCIAL MEDIA MANAGEMENT SERVICE AGREEMENT"
(or "MARKETING SERVICES AGREEMENT" depending on the specific services described)

HEADER BLOCK:
This [Agreement Type] is entered into by and between:
[clientName] (hereinafter referred to as "The Agency" or "The Provider"), [clientAddress]
and
[contractorName] (hereinafter referred to as "The Client"), [contractorAddress]

SECTION 1 — PURPOSE AND SCOPE OF SERVICES:
The purpose of this Agreement is to define the terms and conditions under which [clientName] will provide social media management and content production services, including but not limited to:
[List all selectedContentTypes as bullet points]
Content publishing on the following platforms:
[List each platform from selectedPlatforms]
[If sponsoredPostsCount > 0:] Content creation: [sponsoredPostsCount] posts, [videosCount] videos, [storiesCount] stories
[If servicesDescription is provided:] Additional services: [servicesDescription]
Monitoring and responding to messages and comments on selected platforms.
Engagement strategy and lead generation.
Advertising campaign management on selected platforms.
Monthly performance report.

SECTION 2 — STAGES OF THE AGREEMENT:
The project will be divided into the following phases:

1. Quotation Stage: All activities performed prior to signing this agreement and receiving the initial deposit. NO WORK WILL COMMENCE UNTIL THE DEPOSIT IS RECEIVED.

2. Strategy Development Stage: Begins one (1) business day after the deposit is received. The Agency will conduct research, gather references, and develop a comprehensive creative strategy tailored to The Client's brand objectives. Concludes upon formal approval by The Client.

3. Design/Recording Stage: Starts immediately after strategy approval. Includes creation of design assets and/or recording sessions. Up to [revisionRoundsAllowed] rounds of revisions will be conducted. Concludes once The Client provides written approval.

4. Launching Stage: Commences after final approval of all deliverables. The Agency will prepare and deliver final files and assist with initial implementation. Any modifications or additional requests during this stage will incur an additional charge.

SECTION 3 — TERM AND RENEWAL:
[Based on durationModel / contractDuration:]
This agreement shall have a duration of [contractDurationValue] [contractDurationUnit] from the date of signing.
[If renewalTerm / renewalFrequency specified:] If The Client does not provide written notice of cancellation at least [cancellationNotice] prior to the agreement's expiration date, the contract shall automatically renew under the same terms.
[If durationModel is autoRenewal:] Automatic renewal includes a [%] rate adjustment per renewal period.

SECTION 4 — OBLIGATIONS OF THE PARTIES:
Obligations of The Provider:
- Deliver services described in Section 1 in accordance with industry best practices
- Provide monthly performance reports with metrics and results
- Manage advertising budgets per The Client's needs
- Maintain confidentiality of all information provided by The Client

Obligations of The Client:
- Provide all necessary information, materials, and brand assets for service execution
- Make timely payments as agreed
- Approve content within the established timeframes

SECTION 5 — TIMELINE AND SCHEDULE:
[If campaignStartDate / campaignEndDate provided:] Campaign period: [campaignStartDate] to [campaignEndDate]
[If brandApprovalWindow provided:] Content approval window: [brandApprovalWindow] business days. If no response is received within [brandApprovalWindow] hours/days of delivery, the material will be considered APPROVED BY DEFAULT.
Any changes to the schedule must be approved at least seven (7) days in advance.
Cancellations must be formally communicated via email to the designated representative.

SECTION 6 — FEES AND PAYMENT TERMS:
[Based on compensationModel / compensationAmount:]
- Flat fee: Total service fee: $[compensationAmount] [currency]
- Monthly retainer: Monthly service fee: $[compensationAmount] [currency]
[If depositAmount provided:] Deposit: $[depositAmount], due upon signing.
[If invoiceTiming provided:] Invoice timing: [invoiceTiming]
Payment due: [paymentDue] from invoice date.
[If lateInterest provided:] Late payments will incur a penalty of [lateInterest] per week/month, up to a maximum of 50% of the outstanding amount.
If payment is not received within 15 calendar days, The Provider reserves the right to SUSPEND SERVICES until payment is completed.
[If isNonRefundable:] All fees are NON-REFUNDABLE once work has begun.
If The Client cancels the project within two (2) business days of making the initial deposit, 50% of the deposit will be refunded. After this period, no refunds will be issued.

SECTION 7 — FEES AND PENALTIES:
Work completed up to the date of termination will be billed in full. Termination requires formal written communication via email.

SECTION 8 — INTELLECTUAL PROPERTY:
[Based on ipOwnership:]
- workForHire / client owns: All creative materials, designs, strategies, scripts, and deliverables become the exclusive property of The Client upon full payment.
- Agency retains (default): All creative materials remain the exclusive property of [clientName] until full payment is received. Upon full payment, The Client receives a limited, non-exclusive, non-transferable license to use the content solely for their own business purposes. The Agency retains the right to use completed works for portfolio and promotional purposes.
The Client may not sell, resell, sublicense, or modify any content without The Agency's written authorization.
The Client warrants that any content, logo, or material provided is owned or properly licensed.

SECTION 9 — MODIFICATIONS AND SERVICE CHANGES:
The Client is entitled to [revisionRoundsAllowed] round(s) of revisions per deliverable. Additional revisions will be billed at an additional rate.
If no response is received within 48 hours of delivery, the material will be considered approved by default.
Once approved, any subsequent modification shall require a new quotation.

SECTION 10 — CONFIDENTIALITY AND PROFESSIONAL RELATIONSHIP:
[If confidentiality:] Confidential information will be safeguarded. Neither party shall disparage or defame the other. Breach of this clause may result in legal action.
The Provider may use the material developed for portfolio purposes after delivery, protecting The Client's personal and confidential information.

SECTION 11 — LIMITATION OF LIABILITY:
The Provider shall NOT be liable for:
- Platform algorithm changes or account restrictions
- The Client's misuse of provided materials
- Losses resulting from third-party services
- Expected outcomes such as sales, engagement, or leads
In no event shall The Provider's liability exceed the total fees paid under this Agreement.

SECTION 12 — INDEPENDENT CONTRACTOR STATUS:
The Provider acts as an INDEPENDENT CONTRACTOR. Nothing in this Agreement creates a partnership, employment, or joint venture relationship.

SECTION 13 — NON-SOLICITATION:
The Client agrees not to solicit, hire, or contract directly any employee or subcontractor of The Provider for a period of [24] months following termination of this Agreement.

SECTION 14 — TERMINATION AND CANCELLATION POLICY:
Cancellations made within five (5) business days of payment will receive a 50% refund. No refunds after that period.
Work completed to the date of termination will be billed in full.
Cancellations must be submitted in writing via email to the official representative.

SECTION 15 — JURISDICTION AND DISPUTE RESOLUTION:
[If disputeResolution provided:] Dispute resolution method: [disputeResolution]
This agreement shall be governed and construed in accordance with the laws of the State of [governingLawState]. Disputes shall be resolved in the courts of [governingLawState].

SIGNATURE BLOCK:
The Agency / Provider
Name: [clientName]
Signature: _______________________
Date: ___________________________

The Client
Name: [contractorName]
Signature: _______________________
Date: ___________________________

MANDATORY RULES:
- The 4-stage workflow (Quotation → Strategy → Design → Launch) MUST always appear.
- NO WORK STARTS before deposit is received — always state this.
- Revision rounds are capped at the specified number.
- Client approval (48h implied acceptance) MUST be included.
- IP ownership must specify what happens upon full payment.
- Non-solicitation clause (24 months) MUST appear.
- JURISDICTION: State per governingLawState."""
            },

            # -----------------------------------------------------------------
            # ID 8 — SERVICE AGREEMENT (MAINTENANCE / GENERAL SERVICES)
            # Based on: Maintenance Agreement -Contractors Business Ops.pdf
            # UI: Contractors Business Ops → Service Agreement / Work Order / Job Agreement
            # -----------------------------------------------------------------
            {
                "id": 8,
                "category": "contractors",
                "subcategory": "services",
                "title": "Service Agreement",
                "description": "Acuerdo de prestación de servicios generales o de mantenimiento. Incluye alcance de servicio, tarifas, obligaciones del cliente y exclusiones.",
                "rules": """GENERATE A "SERVICE AGREEMENT" OR "MAINTENANCE AGREEMENT" WITH EXACTLY THIS STRUCTURE:

TITLE: "SERVICE AGREEMENT"
(Use "MAINTENANCE AGREEMENT" if the services described are maintenance/repair type)

HEADER BLOCK:
This Service Agreement ("Agreement") is entered into on [agreementDate], by and between:

Service Provider: [clientName], [clientAddress] (the "Provider")
Customer / Client: [contractorName], [contractorAddress] (the "Client")

PREAMBLE:
The Service Provider agrees to provide services to the Client for [contractDurationValue] [contractDurationUnit] from the date of signing, in accordance with the terms and conditions below.

SECTION 1 — SCOPE OF SERVICES:
The Service Provider agrees to provide the following services:
[List all services from servicesDescription as bullet points]
[If projectType is oneTime:] This is a one-time service engagement.
[If projectType is ongoing:] This is an ongoing service engagement.
[If additionalTasks:] Additional tasks may be requested by written agreement.

SECTION 2 — SERVICE FEE AND PAYMENT:
The fee for services provided under this Agreement shall be $[compensationAmount] [currency].
[Based on compensationModel:]
- flatFee: Fixed fee of $[compensationAmount] payable [invoiceTiming].
- hourlyRate: Hourly rate of $[compensationAmount] per hour.
- retainer: Monthly retainer of $[compensationAmount].
[If depositAmount provided:] Payment of $[depositAmount] is due upon signing.
[If lateInterest provided:] Late payment interest: [lateInterest].
[If paymentDue provided:] Payment due within [paymentDue] of invoice.
[If isNonRefundable:] Payment is due upon signing. This agreement is non-refundable once services have commenced.
[If earlyTermination:] Early termination with pro-rata payment for work completed.

SECTION 3 — TERM:
[Based on durationModel:]
This Agreement is effective from [agreementDate] for [contractDurationValue] [contractDurationUnit].
[If autoRenewal:] This Agreement shall automatically renew for successive periods unless either Party provides [cancellationNotice] written notice of non-renewal.

SECTION 4 — PRICING TIERS (if applicable):
Pricing shall be determined based on the scope of work agreed upon at signing.

SECTION 5 — PROVISIONS OF SERVICES:
The Client and Service Provider have agreed that services are provided on an as-requested or scheduled basis to fulfill the Provider's obligations as described in Section 1.

SECTION 6 — CLIENT'S OBLIGATIONS:
The Client must:
- Promptly notify the Service Provider of any known defects, problems, or complaints
- Provide reasonable access to the premises or materials necessary for service execution
- Clear any obstructions that would prevent the Provider from performing the services
- Make timely payments as agreed

SECTION 7 — ACT OF GOD / FORCE MAJEURE:
[If forceMajeure:] The Service Provider shall not be liable for damages resulting from flooding, earthquakes, hurricanes, or any other acts of God or circumstances beyond the Provider's reasonable control.

SECTION 8 — LIMITATIONS OF WARRANTY:
Any work done by a non-certified third party or without authorization from the Provider voids any warranty or service obligations under this Agreement.
[If warrantyPeriod provided:] The Provider warrants the quality of services for [warrantyPeriod] from the date of completion.

SECTION 9 — LIMITATION OF LIABILITY:
The Provider's liability shall not exceed the total service fee paid under this Agreement.
The Provider shall not be liable for indirect, incidental, or consequential damages.

SECTION 10 — INTELLECTUAL PROPERTY:
[If ipOwnership provided:] All materials, designs, or deliverables produced under this Agreement shall be owned as follows: [based on ipOwnership].

SECTION 11 — CONFIDENTIALITY:
[If confidentialityDuration / nonExclusivity:] Both parties agree to maintain confidentiality of business information exchanged under this Agreement.

SECTION 12 — TERMINATION:
Either party may terminate this Agreement with [cancellationNotice] written notice.
Upon termination, the Client shall pay for all services rendered up to the termination date.

SECTION 13 — GOVERNING LAW:
This Agreement shall be governed by the laws of the State of [governingLaw].

SECTION 14 — ENTIRE AGREEMENT:
This Agreement constitutes the entire agreement between the Parties and supersedes all prior discussions or representations.

SIGNATURE BLOCK:
Service Provider
Name: [clientName]
Signature: _______________________
Date: ___________________________

Customer / Client
Name: [contractorName]
Signature: _______________________
Date: ___________________________

MANDATORY RULES:
- Client obligations (access, notification) MUST always appear.
- Force majeure / Act of God exclusion MUST appear.
- Limitation of liability to fees paid MUST appear.
- Third-party non-authorized work voiding warranty MUST appear.
- JURISDICTION: State per governingLaw input."""
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
