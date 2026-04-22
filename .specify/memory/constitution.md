<!--
Sync Impact Report
- Version change: 1.0.0 → 1.1.0
- List of modified principles:
  - Updated: III. Testing Standards (MANDATORY) → III. Test-Driven Development (TDD)
- Added sections: None
- Removed sections: None
- Templates requiring updates:
  - ✅ .specify/templates/tasks-template.md: Explicitly requirement for TDD workflow.
- Follow-up TODOs: None
-->

# Church Multimedia Management System Constitution

## Core Principles

### I. Code Quality & Maintainability
Follow SOLID principles and Clean Code. Favor readability and maintainability over cleverness. Consistent naming conventions and directory structures are non-negotiable to ensure the codebase remains accessible to all contributors.

### II. Decoupling & Flexibility
Use interfaces (Abstract Base Classes in Python, interfaces in TypeScript) as much as possible for decoupling and flexibility. Favor composition over inheritance to prevent rigid class hierarchies and ensure components are easily swappable and testable.

### III. Test-Driven Development (TDD)
Test-Driven Development is MANDATORY. Unit tests MUST be implemented before the actual code. A feature or bug fix is not considered started until a failing test case is established. This ensures code correctness, improves design, and provides immediate documentation of expected behavior.

### IV. UX Consistency & Performance
Maintain a consistent user experience across the frontend by adhering to established UI patterns and design tokens. Performance is a requirement: aim for Core Web Vitals targets (LCP < 2.5s) and ensure the backend remains responsive under load through efficient query patterns and caching.

### V. Security by Design
Security must be considered at every layer of the stack. Never log or commit sensitive data. Use environment variables for all secrets. Implement robust authentication and authorization, sanitize all inputs, and follow OWASP Top 10 best practices.

## Framework Best Practices

- **Frontend (NextJS)**: Adhere to official NextJS best practices. Use the App Router, favor Server Components for data fetching, and maintain a clear separation between UI components and business logic.
- **Backend (FastAPI)**: Utilize Pydantic for rigorous data validation. Leverage FastAPI's Dependency Injection system for service management. Follow RESTful conventions and maintain clear API versioning.

## Development Workflow & Quality Gates

All code changes must pass the following quality gates before merging:
1. **Linting & Formatting**: Clean runs of ESLint/Prettier (frontend) and Ruff/Black (backend).
2. **Type Safety**: No errors in TypeScript (TSC) or Python type checking (MyPy/Pyright).
3. **Automated Tests**: 100% pass rate for all relevant test suites, following TDD workflow.
4. **Code Review**: At least one approval from a peer focusing on architectural alignment and security.

## Governance
This constitution supersedes all other informal practices. Amendments to these principles require a version bump and a corresponding update to all project templates to ensure continuous alignment.

**Version**: 1.1.0 | **Ratified**: 2026-04-22 | **Last Amended**: 2026-04-22
