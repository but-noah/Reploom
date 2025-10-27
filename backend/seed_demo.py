#!/usr/bin/env python3
"""
Seed script for Reploom demo environment.

This script sets up a complete demo workspace with:
- Demo workspace settings (tone_level=3, blocklist)
- Sample draft review with fake customer email
- No PII - all data is synthetic for demo purposes
"""

import asyncio
import uuid
from datetime import datetime, timezone
from sqlmodel import Session, select

from app.core.db import engine, init_db
from app.models.workspace_settings import WorkspaceSettings
from app.models.draft_reviews import DraftReview


DEMO_WORKSPACE_ID = "demo-workspace"
DEMO_USER_ID = "demo|user123"
DEMO_USER_EMAIL = "demo@reploom.example.com"


async def seed_demo_data():
    """Seed the database with demo data for a smooth 5-minute walkthrough."""

    print("🌱 Starting demo data seeding...")

    # Initialize database schema
    print("📊 Initializing database schema...")
    await init_db()

    with Session(engine) as session:
        # 1. Create demo workspace settings
        print(f"🏢 Creating demo workspace: {DEMO_WORKSPACE_ID}")

        # Check if workspace already exists
        existing_workspace = session.exec(
            select(WorkspaceSettings).where(
                WorkspaceSettings.workspace_id == DEMO_WORKSPACE_ID
            )
        ).first()

        if existing_workspace:
            print(f"   ⚠️  Workspace '{DEMO_WORKSPACE_ID}' already exists, updating...")
            existing_workspace.tone_level = 3
            existing_workspace.style_json = {
                "brand_voice": "professional and helpful",
                "communication_style": "clear and concise"
            }
            existing_workspace.blocklist_json = [
                "free trial",
                "limited time offer",
                "act now",
                "money back guarantee",
                "click here"
            ]
            existing_workspace.approval_threshold = 0.85
            existing_workspace.updated_at = datetime.now(timezone.utc)
            workspace = existing_workspace
        else:
            workspace = WorkspaceSettings(
                workspace_id=DEMO_WORKSPACE_ID,
                tone_level=3,
                style_json={
                    "brand_voice": "professional and helpful",
                    "communication_style": "clear and concise"
                },
                blocklist_json=[
                    "free trial",
                    "limited time offer",
                    "act now",
                    "money back guarantee",
                    "click here"
                ],
                approval_threshold=0.85,
            )
            session.add(workspace)

        session.commit()
        print(f"   ✅ Workspace created/updated: tone_level={workspace.tone_level}")
        print(f"   📝 Blocklist: {len(workspace.blocklist_json)} phrases")

        # 2. Create sample draft reviews for demo
        print("📧 Creating sample draft reviews...")

        sample_drafts = [
            {
                "thread_id": "thread_001_demo",
                "original_message_summary": "Customer asking about account upgrade options",
                "original_message_excerpt": "Hi, I'm interested in upgrading my account to access more features. Can you tell me what options are available?",
                "intent": "support",
                "confidence": 0.92,
                "draft_html": """<p>Hi there!</p>

<p>Thank you for your interest in upgrading your account. We offer three tiers that might work for you:</p>

<ul>
<li><strong>Pro Plan</strong> - $29/month with advanced analytics and priority support</li>
<li><strong>Business Plan</strong> - $79/month with team collaboration and API access</li>
<li><strong>Enterprise Plan</strong> - Custom pricing with dedicated support and custom integrations</li>
</ul>

<p>Each plan includes a 14-day trial period so you can try before committing. Would you like me to send you a detailed comparison of these plans?</p>

<p>Best regards,<br>Support Team</p>""",
                "violations": [],
                "status": "pending"
            },
            {
                "thread_id": "thread_002_demo",
                "original_message_summary": "Customer reporting a login issue",
                "original_message_excerpt": "I can't log into my account. I keep getting an error message that says 'invalid credentials' but I'm sure my password is correct.",
                "intent": "support",
                "confidence": 0.95,
                "draft_html": """<p>Hello,</p>

<p>I'm sorry to hear you're having trouble logging in. Let's get this resolved for you quickly.</p>

<p>Here are a few things to try:</p>

<ol>
<li>Try resetting your password using the "Forgot Password" link on the login page</li>
<li>Clear your browser cache and cookies, then try again</li>
<li>If you're using a password manager, try typing your password manually</li>
<li>Check if Caps Lock is accidentally enabled</li>
</ol>

<p>If none of these work, I can manually reset your account. Just reply to this email and I'll take care of it right away.</p>

<p>Best regards,<br>Support Team</p>""",
                "violations": [],
                "status": "pending"
            },
            {
                "thread_id": "thread_003_demo",
                "original_message_summary": "Sales inquiry about enterprise features",
                "original_message_excerpt": "We're a 50-person company looking for a solution that integrates with our existing CRM. Do you offer SSO and custom integrations?",
                "intent": "cs",
                "confidence": 0.88,
                "draft_html": """<p>Hello,</p>

<p>Thank you for considering Reploom for your team! Yes, our Enterprise plan includes exactly what you're looking for:</p>

<p><strong>Enterprise Features:</strong></p>
<ul>
<li>✅ Single Sign-On (SSO) via SAML 2.0</li>
<li>✅ Custom CRM integrations (Salesforce, HubSpot, and custom REST APIs)</li>
<li>✅ Dedicated account manager</li>
<li>✅ 99.9% uptime SLA</li>
<li>✅ Advanced security features and compliance certifications</li>
</ul>

<p>For a 50-person team, I'd love to schedule a demo to show you how our platform would integrate with your existing workflow. Would next Tuesday or Thursday work for a 30-minute call?</p>

<p>Best regards,<br>Sales Team</p>""",
                "violations": [],
                "status": "approved"
            },
            {
                "thread_id": "thread_004_demo",
                "original_message_summary": "Customer feedback about product feature",
                "original_message_excerpt": "Love the product! One suggestion - it would be great to have dark mode. Any plans to add this?",
                "intent": "other",
                "confidence": 0.75,
                "draft_html": """<p>Hi there!</p>

<p>Thank you so much for the kind words and for sharing your feedback! We really appreciate it.</p>

<p>Dark mode is definitely on our roadmap - you're not the first to request it! We're planning to release it in our next major update, which is scheduled for Q2 next year. I've added your vote to the feature request to help prioritize it.</p>

<p>In the meantime, if you have any other suggestions or run into any issues, please don't hesitate to reach out.</p>

<p>Thanks for being such an engaged user!</p>

<p>Best regards,<br>Product Team</p>""",
                "violations": [],
                "status": "pending"
            },
        ]

        # Check and create/update draft reviews
        for draft_data in sample_drafts:
            thread_id = draft_data["thread_id"]

            existing_review = session.exec(
                select(DraftReview).where(
                    DraftReview.thread_id == thread_id,
                    DraftReview.user_id == DEMO_USER_ID
                )
            ).first()

            if existing_review:
                print(f"   ⚠️  Draft review for {thread_id} already exists, skipping...")
                continue

            review = DraftReview(
                user_id=DEMO_USER_ID,
                user_email=DEMO_USER_EMAIL,
                thread_id=draft_data["thread_id"],
                workspace_id=DEMO_WORKSPACE_ID,
                original_message_summary=draft_data["original_message_summary"],
                original_message_excerpt=draft_data["original_message_excerpt"],
                intent=draft_data["intent"],
                confidence=draft_data["confidence"],
                draft_html=draft_data["draft_html"],
                violations=draft_data["violations"],
                status=draft_data["status"],
                run_id=str(uuid.uuid4()),  # Synthetic run ID
            )
            session.add(review)
            print(f"   ✅ Created draft review: {thread_id} ({draft_data['intent']}, {draft_data['status']})")

        session.commit()

    print("\n✨ Demo data seeding complete!")
    print(f"\n📋 Summary:")
    print(f"   - Workspace: {DEMO_WORKSPACE_ID}")
    print(f"   - User: {DEMO_USER_EMAIL}")
    print(f"   - Sample drafts: {len(sample_drafts)} threads")
    print(f"\n🚀 You're ready to demo! Start the services and navigate to the Inbox page.")


def main():
    """Run the seeding process."""
    asyncio.run(seed_demo_data())


if __name__ == "__main__":
    main()
