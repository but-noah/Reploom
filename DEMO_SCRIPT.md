# Reploom: 5-Minute Demo Script

This script walks you through a complete demonstration of Reploom's core features. Perfect for investor pitches, customer demos, or team showcases.

**Total Time**: 5 minutes
**Audience**: Technical and non-technical stakeholders
**Goal**: Show the complete draft review workflow and key differentiators

---

## Pre-Demo Setup (Do this before presenting)

### 1. Start Services
```bash
cd backend
make up          # Start postgres, redis, qdrant
make migrate     # Initialize database
make seed        # Load demo data
```

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

### 3. Open Browser Tabs
- Tab 1: http://localhost:5173/inbox (Inbox)
- Tab 2: http://localhost:5173/review/[first-draft-id] (Review Page - get ID from Inbox)
- Tab 3: http://localhost:5173/analytics (Analytics)
- Tab 4: http://localhost:5173/settings (Settings)

### 4. Verify Demo Data
- ✅ 4 sample drafts visible in Inbox
- ✅ At least 3 pending, 1 approved
- ✅ Analytics showing intent distribution

---

## Demo Script (5 Minutes)

### Minute 1: Introduction & Problem Statement (60 seconds)

**[Show: Any slide or just speak]**

> "Today I'll show you Reploom - an AI-powered email response system that helps teams draft high-quality replies faster, without sacrificing control.
>
> The problem: Support and sales teams spend hours writing repetitive emails. AI can help, but auto-sending is risky - mistakes, wrong tone, compliance issues.
>
> Our solution: Reploom generates drafts, but **never sends automatically**. Every email gets human review and approval. Let me show you how it works."

**Key points**:
- ✅ Problem: Time spent on email
- ✅ Risk: Auto-send is dangerous
- ✅ Solution: AI drafts + human approval

---

### Minute 2: Inbox - Draft Review Queue (60 seconds)

**[Navigate to: http://localhost:5173/inbox]**

> "This is the Inbox - your draft review queue. Each row is an AI-generated draft waiting for human review.
>
> **[Point to columns]**
> - Original message summary: What the customer asked
> - Intent: Automatically classified (support, sales, executive)
> - Confidence: How sure the AI is (0-100%)
> - Status: Pending, approved, rejected, or editing
>
> **[Demonstrate filtering]**
> - Filter by status to see only pending drafts
> - Filter by intent to prioritize high-value emails (sales, executive)
>
> **[Click on first draft]**
> Let's review this draft in detail."

**Key points**:
- ✅ Central queue for all drafts
- ✅ Automatic classification saves time
- ✅ Filtering helps prioritize

---

### Minute 3: Review Page - Detailed Draft Analysis (90 seconds)

**[Navigate to: http://localhost:5173/review/[draft-id]]**

> "This is the Review page - where you make the go/no-go decision.
>
> **[Point to left side]**
> On the left: The original customer message for context. This is what triggered the draft.
>
> **[Point to right side]**
> On the right: The AI-generated draft. Notice:
> - Professional formatting (HTML-rendered)
> - Appropriate tone (not too formal, not too casual)
> - Structured response (bullet points, clear CTAs)
>
> **[Point to sidebar]**
> Metadata shows:
> - Intent: Support request
> - Confidence: 92% (high confidence)
> - Policy violations: None (more on this in Settings)
> - Run ID: For debugging and traceability
>
> **[Show action buttons]**
> Three options:
> 1. **Approve** - Draft looks good, mark it ready to send (you still send manually from Gmail)
> 2. **Reject** - Draft is wrong, discard it
> 3. **Request Edit** - Provide feedback for a new version (future feature)
>
> **[Click Approve]**
> I'll approve this one. Status changes to 'approved', but **Reploom doesn't send it**. I go to Gmail and manually send when I'm ready."

**Key points**:
- ✅ Full context for informed decisions
- ✅ Clear approve/reject workflow
- ✅ **Never auto-sends** - manual send required

---

### Minute 4: Analytics - Performance Metrics (60 seconds)

**[Navigate to: http://localhost:5173/analytics]**

> "The Analytics page helps you measure team performance and identify trends.
>
> **[Point to Intent Distribution card]**
> - See how many support vs. sales vs. executive emails you're handling
> - Helps with staffing decisions (need more support agents?)
>
> **[Point to Review Rates card]**
> - Approved: 75% (high approval rate means AI is doing well)
> - Rejected: 20% (some drafts need improvement)
> - Editing: 5% (users requesting changes)
> - Pending: 5% (still in queue)
>
> **[Point to First Response Time card]**
> - Average FRT: 2.5 minutes (much faster than manual)
> - SLA met: 85% (meeting 5-minute SLA)
> - Median: 2 minutes (consistent performance)
>
> **[Show time window selector]**
> - Toggle between 7-day and 30-day views
> - Trend indicators show improvement (+12% approval rate!)
>
> This data helps you optimize workflows and justify the investment."

**Key points**:
- ✅ Measure draft quality (approval rate)
- ✅ Track response times (SLA compliance)
- ✅ Identify trends (is AI improving?)

---

### Minute 5: Settings - Workspace Configuration (60 seconds)

**[Navigate to: http://localhost:5173/settings]**

> "Finally, Settings - where you customize Reploom for your brand voice.
>
> **[Point to Tone Level slider]**
> - Tone level: 1 is very formal ('Dear Sir/Madam'), 5 is very casual ('Hey there!')
> - We're at level 3 - professional but approachable
> - **[Move slider to 5, then back to 3]** - Adjust for your audience
>
> **[Point to Blocklist]**
> - Policy enforcement: Block specific phrases
> - 'Free trial', 'limited time offer', 'act now' - flagged as spam-like
> - If the AI uses these, the draft gets flagged in the review UI
>
> **[Point to Style JSON]**
> - Additional brand voice guidelines
> - 'Professional and helpful', 'clear and concise'
> - Advanced users can add custom instructions here
>
> **[Click Save]**
> Changes take effect immediately for new drafts.
>
> This workspace-level config means different teams can have different tone - support uses tone 3, executives use tone 2."

**Key points**:
- ✅ Customizable tone (brand voice)
- ✅ Policy enforcement (blocklist)
- ✅ Workspace-specific (multi-team support)

---

## Closing (30 seconds)

**[Return to any page or close browser]**

> "So that's Reploom in 5 minutes:
>
> 1. **Inbox**: Queue of AI-generated drafts with automatic classification
> 2. **Review**: Full context and approve/reject workflow - **never auto-sends**
> 3. **Analytics**: Measure performance and track trends
> 4. **Settings**: Customize tone and enforce policies
>
> What makes Reploom different?
> - ✅ **Human-in-the-loop**: Every draft reviewed, never auto-sent
> - ✅ **Brand voice control**: Configurable tone and style per workspace
> - ✅ **Policy enforcement**: Blocklist prevents spam-like language
> - ✅ **Full visibility**: Analytics show draft quality and team performance
>
> Next steps: Connect your Gmail, upload knowledge base documents, and start drafting.
>
> Questions?"

---

## Q&A Preparation

### Common Questions

**Q: "Does Reploom send emails automatically?"**
A: No. Reploom **never auto-sends**. All drafts require explicit human approval. Even after approval, you manually send from Gmail. This is by design for safety and compliance.

**Q: "How accurate are the drafts?"**
A: It depends on your knowledge base and tone settings. In our tests, 70-85% of drafts are approved with minimal edits. The approval rate improves as you add more context documents.

**Q: "Can I customize the AI's writing style?"**
A: Yes. Adjust the tone level (1-5 scale), add blocklist phrases, and provide brand voice guidelines in the style JSON. Advanced users can upload company-specific documents for RAG-powered context.

**Q: "What happens if the draft is wrong?"**
A: You reject it. The draft is discarded and never sent. You can also request edits (future feature) to provide feedback and regenerate.

**Q: "Does this work with Outlook/Office 365?"**
A: Not yet. Currently Gmail-only via Google OAuth. Microsoft 365 integration is on the roadmap (see GitHub issues).

**Q: "How do you handle sensitive data?"**
A: See [SAFETY.md](./SAFETY.md). Key points:
- No refresh tokens stored (Auth0 Token Vault)
- PII redacted in logs
- Data residency controls (coming soon)
- User can revoke access anytime
- Self-hosting option for full control

**Q: "Can multiple team members share drafts?"**
A: Yes. Workspaces allow teams to collaborate. Drafts are scoped to the workspace, and all members can review and approve.

**Q: "What's the pricing?"**
A: Reploom is open-source (MIT license). You pay for:
- OpenAI API usage (gpt-4o for drafting)
- Infrastructure (self-host or managed)
- Auth0 fees (if using Token Vault)

**Q: "How long does it take to generate a draft?"**
A: 2-5 seconds on average. Depends on email complexity and knowledge base size.

**Q: "Can I integrate with our CRM (Salesforce, HubSpot)?"**
A: Not yet, but it's on the roadmap. The architecture supports custom tools, so CRM lookups can be added via LangGraph tools.

---

## Alternative Demo Flows

### For Technical Audiences (Add 2-3 minutes)
- Show the LangGraph agent workflow in code
- Explain the Auth0 Token Vault architecture
- Demonstrate the OpenTelemetry tracing (if running Jaeger)
- Walk through the database schema (WorkspaceSettings, DraftReview)

### For Compliance/Legal Teams (Add 2-3 minutes)
- Deep dive into [SAFETY.md](./SAFETY.md)
- Show no auto-send policy enforcement in code
- Explain data retention and deletion
- Discuss GDPR/CCPA compliance gaps and roadmap

### For Sales/Marketing Teams (Focus on benefits)
- Skip technical details
- Focus on time savings ("Draft in 3 seconds, not 3 minutes")
- Highlight approval rates ("85% of drafts approved as-is")
- Show ROI calculation ("1000 emails/week → 8 hours saved")

---

## Post-Demo Actions

### Immediate Follow-up
1. Send link to GitHub repo: https://github.com/but-noah/Reploom
2. Share [SAFETY.md](./SAFETY.md) with compliance team
3. Schedule technical deep-dive (if interested)
4. Offer to run on their own infrastructure (pilot)

### For Pilots
1. Set up Auth0 tenant (guide in README)
2. Connect their Gmail account
3. Upload 5-10 sample documents for KB
4. Run 50-100 drafts for evaluation
5. Collect feedback on tone, accuracy, and workflow

---

## Troubleshooting

### Demo Fails to Start
- **No demo data**: Run `make seed` again
- **Database error**: Run `make clean` (deletes data!), then `make up && make migrate && make seed`
- **Port conflicts**: Check if 5173 (frontend), 8000 (backend), 54367 (LangGraph) are free

### UI Shows No Drafts
- Check browser console for errors
- Verify backend is running: `curl http://localhost:8000/healthz`
- Check database: `make psql`, then `SELECT COUNT(*) FROM draft_reviews;`

### Analytics Shows Zero
- Need at least 1 draft to calculate metrics
- Run `make seed` to populate demo data
- Check date range (demo data uses current date)

---

Last updated: 2025-10-27
Version: 1.0
Maintained by: Reploom Team
