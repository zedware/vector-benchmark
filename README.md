# Vector Search with PostgreSQL and HDF5

This project contains tools for loading high-dimensional vectors from HDF5 files into a PostgreSQL database (using the `pgvector` extension) and benchmarking query performance.

## Prerequisites

- **Python 3.x**
- **PostgreSQL** with the [pgvector](https://github.com/pgvector/pgvector) extension installed.
- **Python Dependencies**:
  ```bash
  pip install h5py psycopg2-binary plotly
  ```

## Tools

### 1. Vector Loader (`load_hdf5.py`)

Loads training vectors from an HDF5 file into a PostgreSQL table. It uses the `COPY` command for high-performance ingestion and supports resuming from a previous run.

**Usage:**
```bash
python load_hdf5.py [options]
```

**Key Arguments:**
- `-f, --hdf5-path`: Path to the HDF5 file.
- `-d, --db-url`: PostgreSQL connection string.
- `-t, --table-name`: Name of the table to create/populate.
- `-D, --dimensions`: Vector dimensions (e.g., 768).
- `-b, --batch-size`: Number of vectors per insertion batch.

---

### 2. Performance Benchmarker (`query_hdf5.py`)

Runs search queries against the database, compares ANN index performance vs. a sequential scan baseline, and calculates the **Recall@k**.

**Usage:**
```bash
python query_hdf5.py [options]
```

**Key Arguments:**
- `-n, --num-queries`: Number of test queries to run.
- `-k`: Number of top results to retrieve.
- `-m, --hint-method`: Choose between `native` (PG settings) or `pg_hint_plan` (hints) to control scan types.
- `-i, --index-name`: Name of the index to force (works with `pg_hint_plan`).
- `-p, --plot`: Generate an interactive HTML plot (`vector_query_performance.html`) of execution times.
- `-v, --verbose`: Print detailed information about each query.

**Features:**
- **Recall Calculation**: Automatically determines the ground truth via forced sequential scans to measure ANN accuracy.
- **pg_hint_plan Support**: Optionally uses the `pg_hint_plan` extension to enforce index usage for precise benchmarking.
- **Interactive Visualization**: Uses Plotly to visualize the performance gap between raw scans and index-backed queries.

## Examples

**Loading data:**
```bash
python load_hdf5.py --hdf5-path data.hdf5 --dimensions 768 --table-name my_vectors
```

**Benchmarking with plotting:**
```bash
python query_hdf5.py --num-queries 100 -k 10 --plot --hint-method native
```
