# Review UI Testing Guide

## Manual E2E Testing

### Prerequisites
1. Backend server running on http://localhost:8000
2. Frontend server running on http://localhost:5173
3. Database initialized with draft_reviews table
4. Valid Auth0 session

### Test Flow: Create and Review a Draft

#### Step 1: Generate a Draft
```bash
# Using curl to create a draft
curl -X POST http://localhost:8000/api/agents/reploom/run-draft \
  -H "Content-Type: application/json" \
  -H "Cookie: auth0_session=..." \
  -d '{
    "message_excerpt": "Customer wants to know how to reset their password",
    "workspace_id": "test-workspace"
  }'
```

Expected Response:
```json
{
  "draft_html": "<p>Dear customer...</p>",
  "confidence": 0.95,
  "intent": "support",
  "violations": [],
  "thread_id": "thread-abc123",
  "run_id": "run-xyz789"
}
```

#### Step 2: Create Review Entry
```bash
curl -X POST http://localhost:8000/api/agents/reploom/reviews \
  -H "Content-Type: application/json" \
  -H "Cookie: auth0_session=..." \
  -d '{
    "thread_id": "thread-abc123",
    "draft_html": "<p>Dear customer...</p>",
    "original_message_summary": "Customer wants to know how to reset their password",
    "intent": "support",
    "confidence": 0.95,
    "violations": [],
    "run_id": "run-xyz789"
  }'
```

#### Step 3: View Inbox
1. Navigate to http://localhost:5173/inbox
2. Verify table shows the new review entry
3. Check columns:
   - Thread shows message summary
   - Intent badge shows "support"
   - Confidence shows "95%"
   - Status shows "pending"
   - Violations shows "None"

#### Step 4: Filter Reviews
1. Click "Status: All" dropdown
2. Select "Pending"
3. Verify only pending reviews are shown
4. Click "Intent: All" dropdown
5. Select "Support"
6. Verify filtering works

#### Step 5: Open Review Detail
1. Click "Review" button on a draft
2. Verify navigation to /review/{id}
3. Verify page shows:
   - Original message excerpt
   - Draft HTML rendered
   - Intent, Confidence, Violations cards
   - Approve, Reject buttons

#### Step 6: Test Edit Flow
1. Click "Edit" button
2. Modify draft HTML in textarea
3. Add edit notes
4. Click "Save Changes"
5. Verify draft version increments
6. Verify status changes to "editing"
7. Verify toast notification appears

#### Step 7: Test Approve Flow
1. Ensure no violations exist
2. Click "Approve" button
3. Verify:
   - Status changes to "approved"
   - Green success banner appears
   - Approve/Reject buttons are hidden
   - Toast notification appears
4. Navigate back to /inbox
5. Verify status badge shows "approved"

#### Step 8: Test Reject Flow
1. Open a pending review
2. Click "Reject" button
3. Modal dialog appears
4. Enter feedback: "Tone is too formal"
5. Click "Reject Draft" in modal
6. Verify:
   - Status changes to "rejected"
   - Red rejection banner appears with feedback
   - Navigation returns to inbox
   - Toast notification appears

### Test Flow: Policy Violations

#### Step 1: Create Draft with Violations
```bash
curl -X POST http://localhost:8000/api/agents/reploom/reviews \
  -H "Content-Type: application/json" \
  -H "Cookie: auth0_session=..." \
  -d '{
    "thread_id": "thread-violation",
    "draft_html": "<p>This draft contains blocked words</p>",
    "original_message_summary": "Test violation",
    "violations": ["Contains blocked term: confidential"]
  }'
```

#### Step 2: Verify Violation Display
1. Navigate to /inbox
2. Verify Violations column shows badge with count
3. Open review detail
4. Verify red violation alert box appears
5. Verify violation messages are listed
6. Verify "Approve" button is disabled

### Automated Testing

#### Unit Tests (Vitest)

Install dependencies:
```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitest/ui
```

Add to package.json:
```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui"
  }
}
```

Create vitest.config.ts:
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
});
```

Run tests:
```bash
npm test
```

#### Integration Tests (Cypress)

Install Cypress:
```bash
npm install -D cypress
```

Create test:
```javascript
// cypress/e2e/review-workflow.cy.js
describe('Review Workflow', () => {
  beforeEach(() => {
    cy.login(); // Custom command for Auth0
  });

  it('should display inbox and allow review', () => {
    cy.visit('/inbox');
    cy.contains('Draft Review Inbox').should('be.visible');

    // Check table exists
    cy.get('table').should('exist');

    // Click first review button
    cy.contains('Review').first().click();

    // Verify detail page
    cy.url().should('include', '/review/');
    cy.contains('Review Draft').should('be.visible');
  });

  it('should allow approving a draft', () => {
    cy.visit('/inbox');
    cy.contains('Review').first().click();

    cy.contains('Approve').click();

    // Verify success
    cy.contains('Draft Approved').should('be.visible');
    cy.url().should('include', '/inbox');
  });

  it('should allow rejecting a draft', () => {
    cy.visit('/inbox');
    cy.contains('Review').first().click();

    cy.contains('Reject').click();

    // Fill feedback
    cy.get('textarea').type('Not appropriate tone');
    cy.contains('Reject Draft').click();

    // Verify navigation
    cy.url().should('include', '/inbox');
  });
});
```

Run Cypress:
```bash
npx cypress open
```

## API Testing

Test backend endpoints:

```bash
# List reviews
curl -X GET http://localhost:8000/api/agents/reploom/reviews \
  -H "Cookie: auth0_session=..."

# Get specific review
curl -X GET http://localhost:8000/api/agents/reploom/reviews/{id} \
  -H "Cookie: auth0_session=..."

# Approve review
curl -X POST http://localhost:8000/api/agents/reploom/reviews/{id}/approve \
  -H "Content-Type: application/json" \
  -H "Cookie: auth0_session=..." \
  -d '{"feedback": "Looks good!"}'

# Reject review
curl -X POST http://localhost:8000/api/agents/reploom/reviews/{id}/reject \
  -H "Content-Type: application/json" \
  -H "Cookie: auth0_session=..." \
  -d '{"feedback": "Not appropriate"}'

# Request edit
curl -X POST http://localhost:8000/api/agents/reploom/reviews/{id}/request-edit \
  -H "Content-Type: application/json" \
  -H "Cookie: auth0_session=..." \
  -d '{
    "draft_html": "<p>Updated content</p>",
    "edit_notes": "Fixed typo"
  }'
```

## Success Criteria

- [ ] Inbox page loads and displays reviews in table format
- [ ] Filtering by status and intent works
- [ ] Review detail page displays all information correctly
- [ ] Edit functionality updates draft and increments version
- [ ] Approve flow marks draft as approved
- [ ] Reject flow captures feedback and marks as rejected
- [ ] Policy violations prevent approval
- [ ] Toast notifications appear for all actions
- [ ] Navigation between pages works smoothly
- [ ] API endpoints return correct status codes and data
