# Vector Benchmark Technical Standards

## Tech Stack
- **Python**: 3.x
- **PostgreSQL**: With `pgvector` extension
- **Dependencies**: `h5py`, `psycopg2-binary`, `plotly`

## Code Style
- Use standard Python library `argparse` for CLI.
- Maintain consistency between `load_hdf5.py` and `query_hdf5.py`.
- Documentation follows standard Markdown.

## Development Workflow
- **Data Files**: HDF5 files should be excluded from version control.
- **Reporting**: Generated HTML reports are ignored to keep the repo clean.
- **Environment**: Use virtual environments (`venv/`) for local development.

## AI Collaboration
- Commits should include co-author attribution for AI collaborators when appropriate.
