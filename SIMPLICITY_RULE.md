# Simplicity Rule - Going Forward

## Core Principle
**Keep code simple, direct, and readable. Avoid unnecessary complexity.**

## Guidelines

### 1. Code Structure
- ✅ Prefer simple functions over complex classes
- ✅ Direct logic over abstractions
- ✅ Clear variable names over clever patterns
- ❌ Avoid over-engineering "just in case"

### 2. Error Handling
- ✅ Simple try/except with clear messages
- ✅ Fail gracefully, log clearly
- ❌ Avoid nested exception handling unless necessary

### 3. Dependencies
- ✅ Use standard libraries when possible
- ✅ Install only what's needed
- ✅ Document why each dependency exists

### 4. Comments
- ✅ Explain "why", not "what"
- ✅ Remove obvious comments
- ❌ Don't comment self-explanatory code

### 5. Functions
- ✅ One clear purpose per function
- ✅ Keep functions short (< 50 lines when possible)
- ✅ Return early, avoid deep nesting

## Examples

**Before (Complex):**
```python
def _initialize_pinecone(self):
    try:
        api_key = os.getenv("PINECONE_API_KEY")
        if api_key:
            try:
                from pinecone import Pinecone
                # ... 20 lines of setup
            except ImportError:
                logger.info("...")
    except Exception as e:
        logger.warning("...")
```

**After (Simple):**
```python
def _initialize_pinecone(self):
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        return
    try:
        from pinecone import Pinecone
        # ... simple setup
    except Exception:
        pass  # Use local storage
```

## Remember
- **Simple code is easier to debug**
- **Simple code is easier to maintain**
- **Simple code is easier to understand**
- **Simple code is production-ready**

