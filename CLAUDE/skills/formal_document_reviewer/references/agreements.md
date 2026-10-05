# Reviewing Agreements

For documents the user is being asked to accept, sign, or click through.

## Scope

- Terms & Conditions / Terms of Service / Terms of Use
- Privacy Policy
- End User License Agreement (EULA)
- Insurance Policy
- Loan / Financing / Credit Agreement
- Subscription Agreement / SaaS Agreement / Service Agreement
- Software License
- Data Processing Agreement
- Acceptable Use Policy

## Review Philosophy

Assume the user wants to know:

- What am I agreeing to?
- What could surprise me later?
- What rights am I giving up?
- What responsibilities am I accepting?
- What could cost me money?
- What could expose me to risk?

Focus attention on clauses that affect the user's rights, obligations, costs, privacy, or operational risk — not on boilerplate that appears in nearly every agreement of this type unchanged.

## Review Criteria

Review the document for: fairness, unusual provisions, hidden obligations, operational impact, financial impact, legal risk, privacy impact, termination conditions, ownership of data, ownership of intellectual property, dispute resolution, and limitations of liability.

## High-Impact Clause Categories

Not every category applies to every document — apply the ones relevant to what you're reviewing (a Privacy Policy won't have loan terms; a loan agreement won't have IP clauses).

### Payments
Automatic renewal, recurring billing, cancellation deadlines, non-refundable payments, price changes, taxes, penalties.

### Termination
Unilateral termination, account suspension, immediate termination, loss of data, notice periods.

### Data & Privacy
Data collection, data sharing, data retention, international transfers, AI training use, third-party access, user tracking.

### Intellectual Property
Ownership of uploaded content, license granted to the provider, perpetual licenses, sublicensing rights, AI-generated content ownership.

### Liability
Liability limitations, warranty disclaimers, indemnification, force majeure, limitation of damages.

### User Obligations
Prohibited activities, compliance requirements, security responsibilities, account responsibilities, acceptable use.

### Service Changes
Unilateral changes, feature removal, service discontinuation, modification without notice.

### Dispute Resolution
Mandatory arbitration, class action waiver, governing law, jurisdiction, venue.

### Security
Security guarantees, breach notification, backup responsibility, availability commitments, SLA references.

### Insurance-Specific Clauses
When reviewing an insurance policy, these usually matter more than the generic categories above:

- **Coverage vs. exclusions** — what's explicitly covered, and what's carved out. Exclusions are where most disputes originate; read them as closely as the coverage grants.
- **Deductibles vs. policy limits** — what the user pays out of pocket before coverage kicks in, and the maximum the insurer will ever pay (per claim and/or per policy period).
- **Waiting periods** — time between policy start and when coverage actually becomes active for certain claim types (common in health/life policies).
- **Pre-existing condition clauses** — whether prior conditions/history are excluded, and for how long.
- **Claims process & denial grounds** — what's required to file a claim, typical processing time, and the stated grounds on which a claim can be denied.
- **Premium escalation & renewal terms** — whether premiums can increase at renewal, under what conditions, and whether renewal is guaranteed or at the insurer's discretion.
- **Cancellation / lapse conditions** — what causes a policy to lapse (e.g., missed payment grace period) and whether coverage gaps result.
- **Subrogation** — whether the insurer can pursue a third party (or the user) to recover what it paid out.
- **Riders / endorsements** — add-ons that modify the base policy; note what they actually change.

### Loan / Financing Agreement-Specific Clauses
When reviewing a loan, credit, or financing (leasing) agreement, prioritize:

- **Interest structure** — flat rate vs. effective/declining-balance rate (*bunga flat* vs. *bunga efektif/anuitas* in Indonesian financing docs); these produce very different real costs for the same stated percentage. Flag if the type isn't clearly stated.
- **All-in cost** — admin fees, provision fees, insurance bundling, notary fees, and other charges added on top of the headline rate.
- **Late payment fees / denda** — the rate and how it compounds.
- **Prepayment / early settlement terms** (*pelunasan dipercepat*) — whether early payoff is allowed, and any penalty for doing so.
- **Default triggers & grace period** — what constitutes default, how many days' grace before consequences start.
- **Collateral / jaminan and repossession rights** — what's pledged as collateral, whether it's a *fiducia* (jaminan fidusia) arrangement, and what process the lender must follow before repossessing (this is a frequent source of disputes in Indonesian consumer financing — note whether the agreement describes a lawful repossession process or is vague/silent on it).
- **Guarantor / penjamin obligations** — what a co-signer or guarantor is actually on the hook for.
- **Acceleration clause** — whether a single missed payment can make the entire remaining balance due immediately.
- **Mandatory insurance bundling** — whether the borrower is required to buy insurance through the lender, and on what terms.
- **Assignment** — whether the lender can sell/transfer the debt to a third party (e.g., a collections agency) without the borrower's consent.

## Unusual or Non-Standard Terms

Identify clauses that are significantly more restrictive or permissive than commonly found in similar agreements, and explain *why* they're unusual. Examples: perpetual rights over user content, broad indemnification obligations pushed one-way onto the user, unusually broad data sharing, unlimited liability for the user, one-sided termination rights, unilateral contract modification, mandatory arbitration with limited appeal, broad monitoring rights, uncapped or vaguely-defined default/penalty fees.

## Implicit Consequences

Look beyond the literal wording to the practical effect.

> Clause: "The provider may terminate your account at any time."
> Practical implication: "You may lose access to your data unless you maintain your own backups."

## Risk Assessment

For every significant finding, provide:

- **Clause** — short description
- **Why It Matters** — plain-language explanation
- **Potential Impact** — Financial / Operational / Privacy / Legal / Business continuity
- **Severity** — Critical / High / Medium / Low / Informational

## Positive Findings

Also identify user-friendly provisions: clear cancellation process, reasonable notice periods, strong privacy protections, transparent pricing, data portability, customer ownership of data, fair limitation of liability, guaranteed renewal terms, clearly defined claims/repossession processes.

## Missing Information

Flag important topics that are absent: no privacy explanation, no data retention policy, no termination procedure, no SLA, unclear ownership, unclear refund policy, no stated repossession process, no clear claims-denial appeal path.

## Deliverables

Produce the review in this structure (translate headers per the glossary in SKILL.md if writing in Bahasa Indonesia):

```text
## Executive Summary
Overall assessment — what kind of document this is and the bottom line.

## Major Findings
High-impact clauses.

## Unusual Terms
Clauses that differ from common practice.

## Practical Implications
What agreeing to the document means in practice.

## Positive Provisions
User-friendly protections.

## Missing or Unclear Areas
Important topics that are absent or ambiguous.

## Risk Summary
| Severity | Count |
| --- | ---: |
| Critical | |
| High | |
| Medium | |
| Low | |

## Recommendations
Questions the user should consider before accepting the agreement.
```

The goal is not to determine whether the agreement is "good" or "bad." The goal is to help the user understand the most important consequences of accepting it.
