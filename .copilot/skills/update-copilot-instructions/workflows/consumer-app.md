# Consumer App Workflow

**Project Type**: Web frontends, mobile apps, CLI clients, desktop applications

**Applies to**: Applications that consume APIs or services; focuses on user-facing features

**Key Focus**: UI/UX, state management, user interaction, API client patterns

---

## Workflow Steps

### 1. Analyze the Consumer App

Read these files to understand the application:

- `README.md` - What does this app do?
- `package.json`, `pyproject.toml`, or equivalent - What framework? (React, Vue, Angular, etc.)
- Folder structure - How are components/pages organized?
- State management - What's the approach? (Redux, Zustand, Context, etc.)
- API integration - What services does it consume?
- Configuration - How is it configured?

**Questions to answer**:

- What is the main purpose of this app?
- What framework/language is used (React, Vue, Flutter, etc.)?
- Who are the users (consumers, internal staff, etc.)?
- What APIs/services does it consume?
- What are the main features/pages?
- How is state managed?

---

### 2. Fill Project Identity Section

Update the `PROJECT CONTEXT` section in `[projectWorkspace]/.github/copilot-instructions.md`:

```markdown
**Project Name**: [Actual app name, e.g., "dashboard-ui", "order-mobile-app"]

**Description**: [1-2 sentences describing what the app does and who uses it]
Example: "Web dashboard for order management, allowing users to view, create, and track orders in real-time."

**Project Type**: Consumer App

**Language**: JavaScript/TypeScript (or Python, Swift, Kotlin, etc.)
**Framework**: React 18+ (or Vue, Angular, Flutter, etc.)
**Key Dependencies**: [List main deps, e.g., "React, React Router, Redux Toolkit, Axios, Jest"]
```

---

### 3. Add Project-Specific Patterns

Document unique conventions for THIS consumer app:

```markdown
**Project-Specific Patterns & Conventions**:
- Component Structure: Functional components with hooks; custom hooks for logic reuse
- State Management: Redux Toolkit for global state; useContext for local feature state
- API Integration: Custom axios instance with interceptors; React Query for caching/sync
- Styling: Tailwind CSS for utility-first styling; CSS modules for component-scoped styles
- Routing: React Router v6 with nested routes; lazy loading for code splitting
- Forms: React Hook Form for validation; Zod for schema validation
- Testing: Jest for unit tests, React Testing Library for component tests, Cypress for E2E
- Error Handling: Consistent error boundaries; user-friendly error messages; error tracking (Sentry)
- Performance: Code splitting by route; image optimization; bundle size monitoring
- Accessibility: WCAG 2.1 AA compliance; semantic HTML; keyboard navigation
```

---

### 4. Select Awesome-Copilot References

**Always include these** (all projects):

- Code Generation Guidelines
- Security Standards (OWASP)
- AI Prompt Engineering & Safety
- Markdown Content Rules
- GitHub Flavored Markdown
- GitHub Actions CI/CD Best Practices

**Add these for JavaScript/TypeScript frontends**:

- [JavaScript/TypeScript Development](https://github.com/github/awesome-copilot/blob/main/instructions/javascript-typescript.instructions.md)

**Add these if applicable**:

- [Frontend Component Design](https://github.com/github/awesome-copilot/blob/main/instructions/frontend-components.instructions.md) ← For React/Vue/Angular
- [State Management Patterns](https://github.com/github/awesome-copilot/blob/main/instructions/state-management.instructions.md) ← For Redux/Vuex/MobX
- [API Client Patterns](https://github.com/github/awesome-copilot/blob/main/instructions/api-client-patterns.instructions.md) ← For API integration
- [Form Handling & Validation](https://github.com/github/awesome-copilot/blob/main/instructions/form-validation.instructions.md) ← For forms
- [Performance & Optimization](https://github.com/github/awesome-copilot/blob/main/instructions/performance-optimization.instructions.md) ← For web perf
- [Testing Web Applications](https://github.com/github/awesome-copilot/blob/main/instructions/testing-web-apps.instructions.md) ← For Jest/Testing Library/Cypress
- [Accessibility (a11y)](https://github.com/github/awesome-copilot/blob/main/instructions/accessibility.instructions.md) ← For WCAG compliance

**Example reference section**:

```markdown
### Language/Framework-Specific References

**For JavaScript/TypeScript projects**:
- [JavaScript/TypeScript Development](https://github.com/github/awesome-copilot/blob/main/instructions/javascript-typescript.instructions.md)

**For React applications**:
- [React Component Design](https://github.com/github/awesome-copilot/blob/main/instructions/react.instructions.md)
- [State Management with Redux](https://github.com/github/awesome-copilot/blob/main/instructions/redux.instructions.md)

**For API integration**:
- [API Client Patterns](https://github.com/github/awesome-copilot/blob/main/instructions/api-client-patterns.instructions.md)

**For forms**:
- [Form Handling & Validation](https://github.com/github/awesome-copilot/blob/main/instructions/form-validation.instructions.md)

**For testing**:
- [Testing Web Applications](https://github.com/github/awesome-copilot/blob/main/instructions/testing-web-apps.instructions.md)

**For performance**:
- [Web Performance Optimization](https://github.com/github/awesome-copilot/blob/main/instructions/performance-optimization.instructions.md)

**For accessibility**:
- [Web Accessibility (WCAG)](https://github.com/github/awesome-copilot/blob/main/instructions/accessibility.instructions.md)
```

---

### 5. Document Project-Specific Instructions

If your app has special instructions in `.github/instructions/`, document them:

```markdown
## Project-Specific Instructions & Files

This consumer app has the following project-specific instructions:

**component-development.md**
- Description: Guidelines for creating reusable React components, hooks, and patterns
- When to use: When building new components or features
- Location: `.github/instructions/component-development.md`

**state-management.md**
- Description: Standards for Redux actions, reducers, selectors, and state organization
- When to use: When modifying global state or adding new features
- Location: `.github/instructions/state-management.md`

**api-integration.md**
- Description: Patterns for API calls, caching, error handling, and data fetching
- When to use: When integrating with backend services
- Location: `.github/instructions/api-integration.md`
```

If no special instructions:

```markdown
## Project-Specific Instructions & Files

This consumer app follows standard React/web development conventions. See the awesome-copilot references above for detailed guidance on component design, state management, and testing.
```

---

### 6. Validate Changes

**Checklist**:

- [ ] App name is accurate (e.g., "dashboard-ui", not "[PROJECT_NAME]")
- [ ] Description explains what the app does and who uses it (1-2 sentences)
- [ ] Project Type is "Consumer App"
- [ ] Language and Framework are correctly specified (React, Vue, etc.)
- [ ] Tech Stack includes key dependencies (React, Redux, testing libs, etc.)
- [ ] Project-Specific Patterns describe actual conventions (components, state, API, styling, etc.)
- [ ] All awesome-copilot links are correct and applicable to web apps
- [ ] Entry Point Information section was NOT modified
- [ ] No task-specific file mappings added
- [ ] All sections are filled (no empty placeholders remain)

---

### 7. Update Metadata

Change the Last Updated section at the bottom:

```markdown
## Last Updated

- **Date**: April 22, 2026
- **Status**: Project context complete
- **Author**: GitHub Copilot
```

---

## Example: Order Management Dashboard

**Before**:

```markdown
**Project Name**: [PROJECT_NAME]

**Description**: [DESCRIBE PROJECT HERE]

**Project Type**: [API Service / Consumer App / Data Pipeline / Library / Other]

**Language**: [e.g., Python 3.9+]
```

**After**:

```markdown
**Project Name**: order-dashboard

**Description**: React-based web dashboard for order management, allowing support staff to view, update, and track customer orders in real-time.

**Project Type**: Consumer App

**Language**: JavaScript/TypeScript (ES2022+)
**Framework**: React 18+ with TypeScript
**Key Dependencies**: React Router, Redux Toolkit, React Query, Tailwind CSS, React Hook Form, Jest, Cypress
```

**Project-Specific Patterns Example**:

```markdown
**Project-Specific Patterns & Conventions**:
- Components: Functional React components with hooks; custom hooks extracted to `hooks/` folder
- State Management: Redux Toolkit with slices; async thunks for API calls; selectors for derived state
- API Calls: React Query for server state; custom useApi hook for consistent error handling
- Styling: Tailwind CSS with custom config; component-scoped CSS modules for complex styling
- Routing: React Router v6 with nested routes; protected routes for authentication
- Forms: React Hook Form with Zod validation; custom form components for consistency
- Testing: Jest for unit tests; React Testing Library for component tests; Cypress for E2E flows
- Error Handling: Global error boundary; Toast notifications for user feedback; Sentry for error tracking
- Performance: Code splitting by route using React.lazy; Image optimization; Bundle analysis in CI
- Accessibility: WCAG 2.1 AA target; Semantic HTML; Keyboard navigation for all interactive elements
```

**References Example**:

```markdown
### Language/Framework-Specific References

**For JavaScript/TypeScript projects**:
- [JavaScript/TypeScript Development](https://github.com/github/awesome-copilot/blob/main/instructions/javascript-typescript.instructions.md)

**For React applications**:
- [React Component Design](https://github.com/github/awesome-copilot/blob/main/instructions/react.instructions.md)
- [State Management (Redux Toolkit)](https://github.com/github/awesome-copilot/blob/main/instructions/redux-toolkit.instructions.md)

**For API integration**:
- [API Client Patterns & React Query](https://github.com/github/awesome-copilot/blob/main/instructions/api-client-patterns.instructions.md)

**For form handling**:
- [Form Validation & React Hook Form](https://github.com/github/awesome-copilot/blob/main/instructions/form-validation.instructions.md)

**For testing**:
- [Testing React Applications](https://github.com/github/awesome-copilot/blob/main/instructions/testing-web-apps.instructions.md)

**For performance**:
- [Web Performance & Code Splitting](https://github.com/github/awesome-copilot/blob/main/instructions/performance-optimization.instructions.md)

**For accessibility**:
- [Web Accessibility (WCAG 2.1)](https://github.com/github/awesome-copilot/blob/main/instructions/accessibility.instructions.md)
```

---

## Success Criteria

✅ App name, description, and type accurately reflect this consumer app
✅ Language and Framework are correctly specified (React, Vue, etc.)
✅ Tech Stack lists actual dependencies and tools
✅ Project-Specific Patterns describe real conventions (components, state, API, styling, testing)
✅ All placeholder text `[EXAMPLE]` is replaced with actual values
✅ Awesome-copilot references are relevant to web/app development
✅ Entry Point Information section was NOT modified
✅ Last Updated date is current
✅ No task-specific file mappings were added
✅ Documentation is specific to this app's architecture

---

## Tips for Consumer Apps

- **Framework**: Be clear about framework and major version (React 18, Vue 3, etc.)
- **State Management**: Document the chosen state management approach (Redux, Context, Zustand, etc.)
- **API Client**: Describe the API client pattern (axios, fetch, React Query, SWR, etc.)
- **Styling**: Mention CSS approach (Tailwind, styled-components, BEM, etc.)
- **Testing**: List testing tools and coverage expectations
- **Build Tool**: Mention build tool (Webpack, Vite, Parcel, etc.)
- **Deployment**: Document deployment targets (Vercel, S3, etc.)
