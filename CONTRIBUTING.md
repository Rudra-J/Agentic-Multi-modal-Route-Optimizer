# Contributing to Agentic Auto Routing System

Thank you for your interest in contributing! This guide will help you get started.

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Git
- OpenRouter API key (free tier available)

### 1. Fork & Clone

```bash
# Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/agentic-auto-routing.git
cd agentic-auto-routing
```

### 2. Set Up Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp .env.example .env

# Edit .env with your OpenRouter API key
# Get a free key at https://openrouter.ai/
```

### 3. Verify Setup

```bash
# Run tests
python test_harness.py
python test_leg_constraint_integration.py

# Start server
uvicorn main:app --reload --port 8001

# Visit http://127.0.0.1:8001/
```

## 📝 Making Changes

### Code Style
- Follow PEP 8
- Use type hints in function signatures
- Add docstrings to functions

### Example:
```python
def route_optimization(locations: List[str], avoid_modes: Set[str]) -> Dict:
    """
    Optimize route across multiple locations.
    
    Args:
        locations: List of location names
        avoid_modes: Set of transport modes to avoid
    
    Returns:
        Dictionary with optimized route and metadata
    """
    # Implementation here
    pass
```

### Testing
- Add tests for new features in `tests/` directory
- Run the test suite before making a pull request

```bash
python test_harness.py          # Full test suite
python test_leg_avoid_comprehensive.py  # Constraint tests
```

### File Organization

**Core Logic**:
- `agents/` - Multi-agent orchestration
- `models/` - Data models (Pydantic)
- `services/` - Business logic services
- `data/` - Transport network data

**UI**:
- `index.html` - Frontend application
- `main.py` - API entry point

**Documentation**:
- `README.md` - Project overview
- `RESUME_WRITEUP.md` - Technical deep-dive

## 🐛 Reporting Bugs

Create an issue with:
1. **Title**: Brief description of the bug
2. **Reproduction steps**: How to reproduce it
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happened
5. **Environment**: Python version, OS

Example:
```
Title: Leg-specific constraint not applying on metro routes

Reproduction:
1. Add meetings to Andheri and Bandra
2. Say "avoid metro from Andheri to Bandra"
3. Plan the day
4. Metro still appears in route

Expected: Route should use train/cab/bus instead
Actual: Route uses metro despite constraint

Environment: Python 3.9, Windows 10
```

## 💡 Suggesting Features

Create an issue with:
1. **Feature description**: What you want to add
2. **Motivation**: Why it's useful
3. **Implementation idea**: How you'd approach it (optional)

Example:
```
Title: Real-time traffic integration

Description: Add live traffic APIs to dynamically update travel times

Motivation: Routes become outdated quickly during rush hour

Implementation: 
- Integrate Google Maps API or similar
- Update edge weights every 5 minutes
- Trigger re-planning if times change significantly
```

## 🔄 Submitting Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming:
- `feature/description` - New feature
- `fix/bug-description` - Bug fix
- `docs/improvement` - Documentation
- `test/scenario` - New tests

### 2. Make Changes

```bash
# Edit files, test thoroughly
python test_harness.py  # Run before commit

# Stage changes
git add .

# Commit with clear message
git commit -m "Add feature: X

- Implemented Y functionality
- Updated Z documentation
- Added tests for new behavior"
```

### 3. Push & Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
# - Link to any related issues
# - Describe your changes
# - Explain why this is useful
```

### 4. Code Review

- Respond to feedback
- Update code if needed
- Push additional commits to the same branch

## 🎯 Areas for Contribution

### High Priority
- [ ] Real-time traffic data integration
- [ ] Geographic visualization (map display)
- [ ] User preference learning (ML model)
- [ ] Database for storing user histories

### Medium Priority
- [ ] Multi-day planning
- [ ] User authentication
- [ ] API rate limiting
- [ ] Enhanced error messages

### Low Priority
- [ ] Different language support
- [ ] Alternative transport modes
- [ ] Mobile app version

## 📚 Project Structure

Learn about:
- **Route Optimization**: See `agents/planner_agent.py`
- **NLP Parsing**: See `agents/brain_agent.py`
- **State Management**: See `models/world_state.py`
- **Transport Network**: See `data/mumbai_routes.py`

## 💬 Communication

- **Issues**: For bugs and feature requests
- **Discussions**: For questions and ideas
- **Pull Requests**: For code contributions

## 📋 Contribution Checklist

Before submitting a PR, ensure:

- [ ] Code follows PEP 8 style guide
- [ ] All tests pass: `python test_harness.py`
- [ ] New features include tests
- [ ] Documentation is updated
- [ ] No hardcoded secrets or API keys
- [ ] Commit messages are clear
- [ ] Branch is up-to-date with `main`

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [NetworkX Guide](https://networkx.org/)
- [Pydantic Validation](https://docs.pydantic.dev/)
- [Git Workflow](https://www.atlassian.com/git/tutorials)

## ❓ Questions?

- Check existing issues and discussions
- Review the README and documentation
- Look at test files for usage examples

## 🙏 Thank You!

Your contributions help make this project better for everyone. We appreciate your time and effort!

---

**Happy coding!** 🚀
