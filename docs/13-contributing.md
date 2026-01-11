# Development Guidelines

This document provides development workflow guidelines for the SFS BusNest development team.

## Getting Started

1. **Clone the repository**
```bash
git clone https://github.com/joisemp/sfs-busnest.git
cd sfs-busnest
```

2. **Set up the development environment** (see [Getting Started](./01-getting-started.md))

3. **Create a branch** for your work

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-description
```

## Development Workflow

### 1. Before You Start

- Check with the team lead for task assignment
- Review existing issues/tickets to avoid duplicate work
- Discuss major architectural changes with the team
- Review the [Conventions](./11-conventions.md) document

### 2. Making Changes

#### Code Changes
- Follow [PEP 8](https://pep8.org/) style guide
- Write meaningful commit messages
- Add docstrings to new functions/classes
- Update relevant documentation

#### Model Changes
- Create migrations: `docker exec -it sfs-busnest-container python manage.py makemigrations`
- Test migrations: `docker exec -it sfs-busnest-container python manage.py migrate`
- Include `org` field for multi-tenancy
- Auto-generate slugs
- Add docstrings

#### View Changes
- Use appropriate access mixins
- Filter by organisation
- Optimize queries with `select_related`/`prefetch_related`
- Add docstrings

#### Template Changes
- Extend base templates
- Use Bootstrap classes
- Include CSRF tokens in forms
- Keep HTMX patterns consistent

#### Static File Changes
- Edit .scss files, not .css
- Use Bootstrap variables
- Test responsiveness

### 3. Testing

#### Run Tests Before Committing
```bash
# Windows PowerShell
cd src
$env:DJANGO_SETTINGS_MODULE="config.test_settings"
python manage.py test
$env:DJANGO_SETTINGS_MODULE="config.settings"

# Linux/Mac
cd src
DJANGO_SETTINGS_MODULE=config.test_settings python manage.py test
```

#### Write Tests for New Features
```python
# services/test/test_models.py
class NewFeatureTestCase(TestCase):
    def setUp(self):
        # Setup test data
        pass
    
    def test_feature_works(self):
        # Test your feature
        self.assertEqual(expected, actual)
```

### 4. Documentation

Update documentation for:
- New features
- API changes
- Configuration changes
- Deployment changes

Documentation files are in `docs/` directory.

### 5. Commit Messages

Follow conventional commits format:

```
feat: Add stop transfer drag-and-drop interface
fix: Correct trip booking count on ticket deletion
docs: Update architecture documentation
style: Format code with black
refactor: Reorganize models into separate files
test: Add tests for stop transfer utility
chore: Update dependencies
```

**Format:**
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

### 6. Pull Request Process

#### Before Submitting
- [ ] Tests pass
- [ ] Code follows conventions
- [ ] Documentation updated
- [ ] Migrations created if needed
- [ ] No sensitive data in commits

#### Create Pull Requesthe repository
2. Create PR on GitHub targeting the appropriate branch (usually `main`)
3. Fill out PR template completely
4. Link related issues/tickets
5. Request review from team memberte completely
4. Link related issues

#### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Commented complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] Tests pass
- [ ] No new warnings
```

#### After Submission
- Respond to review comments
- Make requested changes
- Keep PR updated with main branch

## Code Review

### As a Reviewer
- Be constructive and respectful
- Test the changes locally
- Check for:
  - Code quality
  - Test coverage
  - Documentation
  - Performance implications
  - Security concerns

### As an Author
- Be open to feedback
- Explain your decisions
- Make requested changes promptly
- Thank reviewers

## Issue Guidelines

### Reporting Bugs

Create an issue using the bug report template:

```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. Scroll down to '...'
4. See error

**Expected behavior**
What you expected to happen

**Screenshots**
If applicable

**Environment:**
- OS: [e.g. Windows 11]
- Browser: [e.g. Chrome 91]
- Docker version: [e.g. 20.10.7]

**Additional context**
Any other information
```

### Feature Requests

Create an issue using the feature request template:

```markdown
**Is your feature request related to a problem?**
Clear description of the problem

**Describe the solution you'd like**
Clear description of what you want

**Describe alternatives you've considered**
Other solutions you've thought about

**Additional context**
Any other information, mockups, etc.
```

## Development Best Practices

### 1. Security
- Never commit sensitive data
- Use environment variables for secrets
- Validate all user input
- Use Django's built-in security features

### 2. Performance
- Optimize database queries
- Use indexes appropriately
- Implement caching where beneficial
- Profile slow operations

### 3. Maintainability
- Write clean, readable code
- Add comments for complex logic
- Keep functions focused and small
- Follow DRY principle

### 4. Testing
- Write tests for new features
- Maintain test coverage
- Test edge cases
- Test error conditions

## Project Structure

When adding new files, follow this structure:

```
src/
├── services/
│   ├── models/           # Add to appropriate file
│   ├── views/            # Add to role-specific file
│   ├── forms/            # Add to role-specific file
│   ├── urls/             # Add to role-specific file
│   └── utils/            # Add utility functions here
├── templates/
│   └── {role}/           # Add to role folder
├── static/
│   ├── styles/{role}/    # Add SCSS here
│   └── js/               # Add JavaScript here
└── tests/
    └── test_*.py         # Add tests here
```

## Release Process

### Version Numbering
Follow [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Changelog
Update CHANGELOG.md with:
- New features
- Bug fixes
- Breaking changes
- Deprecations
Team Communication

### Communication Channels
- **GitHub Issues**: Bug tracking and feature requests
- **Pull Requests**: Code review and technical discussion
- **Team Meetings**: Sprint planning and architectural decisions
- **Direct Communication**: Quick questions and clarifications

### Team Guidelines
- Be respectful and professional
- Provide constructive feedback in code reviews
- Share knowledge with team members
- Ask questions when unclear
- Document decisions and changes

## Questions?

- Check [Documentation](./README.md)
- Search existing issues and PRs
- Ask team members
- Reach out to team lead or senior developers

## Code Ownership

- All code is owned by the organization
- Follow company coding standards
- Maintain confidentiality of proprietary code
- Do not share code or credentials externally

Thank you for being part of the SFS BusNest development team
Thank you for contributing to SFS BusNest! 🚀
