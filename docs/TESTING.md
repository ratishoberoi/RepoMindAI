# Testing Guide

Run:

```bash
PYTHONPATH=backend pytest
```

The suite covers:

- Ignore rules and hashing
- File classification
- Parser utilities
- Dependency graph generation
- Report generation
- Model adapter selection
- API health, local import, analysis, reports, and chat
- End-to-end analysis of a FastAPI sample repository

Heavy model loading is intentionally not part of the default test run.
