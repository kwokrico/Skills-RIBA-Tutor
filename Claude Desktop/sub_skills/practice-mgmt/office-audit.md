# Practice Management: Office Audit

## Purpose
Use this playbook when the exam asks you to audit NDG Architects’ staffing, salary table, charge-out rates, role changes, insurance adequacy, or practice capacity.

## Output constraint (verbatim line)
End the setup response with:
> Claude RIBA Part III is at your service. Practice Audit complete.

## A. Personnel Table Template (Salary + Charge-out)
Fill using scenario facts. If a field is not stated, mark **TBC** and state the assumption separately.

| Name | Current job title | Salary (pa) | Charge-out rate (£/hr) | Expertise | Notes |
|---|---:|---:|---:|---|---|
|  |  |  |  |  |  |

### Charge-out rate logic (quick)
- **Rule of thumb**: charge-out rate must cover **salary + on-costs + overhead recovery + profit**.\n- If asked to justify rates, cross-check with `financial-health.md` (net multiplier / overhead recovery).

## B. Notable Changes (Position Changes / Leavers)
Extract every role change, departure, or new hire and present:

| Person | Change | Effective date (if stated) | Stated reason | Risk to NDG / mitigation |
|---|---|---|---|---|
|  |  |  |  |  |

## C. Practice Health Check (Insurance + Governance)
Use as a checklist; convert to a short RAG assessment if time is tight.

### C1. Insurance checklist (typical for UK practice)
- **Professional Indemnity Insurance (PII)**: adequate limit for project value/complexity; check exclusions; confirm retroactive date.\n- **Public Liability (PL)**: in place and adequate.\n- **Employers’ Liability (EL)**: statutory compliance.\n- **Cyber / data**: if handling client data / BIM / cloud workflows.\n- **Run-off awareness**: if a director hints at closing a practice or changing entity (see `insurance-liability/pii-claims.md`).\n
### C2. Competence / dutyholder capability (CDM/BSA cues)
- If PD/Principal Designer role is mentioned or implied, confirm competence/resources and document appointments.\n- If HRB/BSA is in play, ensure named dutyholders and competence evidence (see `legal-safety/building-safety.md`).\n
### C3. Capacity check (headline)
- Identify whether the staff mix can deliver the stated programme.\n- If asked to quantify capacity or stage hours, use `resource-planning.md`.

## D. Setup response template (what to output)
1) **Exam title**: identify season/year.\n2) **Confirm 10 practice problems**: list their headings/titles as found.\n3) **Personnel table** + **Notable changes**.\n4) **Practice Health Check**: key adequacy statement + 3–5 risks.\n5) Close with the required verbatim line.

