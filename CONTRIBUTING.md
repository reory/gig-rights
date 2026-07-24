# Contributing to Gig-Rights

Thanks for taking the time to contribute to **Gig-Rights**! 

---

## 🚀 Development Setup

### **Fork & clone the repository:**
```bash
git clone [https://github.com/reory/gig-rights.git](https://github.com/reory/gig-rights.git)
cd gig-rights
```
### Set up your environment:

- Local Python:
```Bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### Docker (Recommended):

```Bash
make up
```

---

## 🛠️ Guidelines & Code Standards
Branching: Create a descriptive branch name (feature/short-description or fix/issue-description).

### Code Style: 
- Follow PEP 8 and use explicit Python type hints.

### Audit Integrity: 
- Ensure any core domain or database changes maintain the append-only audit trail required for compliance.

### Testing: 
- All new features or bug fixes must include corresponding pytest tests.

### 🧪 Running Quality Checks
Run the test suite locally or inside Docker before opening a PR:

### Run tests locally
```Bash
pytest
```

### Or run tests in Docker
```bash
make test-docker
```

---

## 📥 Submitting a Pull Request
- Push your branch to your fork:

```Bash
git push origin feature/your-feature-name
```
- Open a Pull Request targeting the main branch.

- Include a short summary of the changes and link any related issues.

- Happy coding 😊