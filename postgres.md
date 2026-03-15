
## Vector queries

Load 1 million rows into the table using `vector/load_hdf5.py`.

Postgres's SERIAL starts with 1, but cohere's neighbor IDs start with 0. So we need to subtract 1 from the neighbor IDs to match the expected HDF5 ground truth indices.

```
postgres=# \d cohere_vectors
                                Table "public.cohere_vectors"
  Column   |    Type     | Collation | Nullable |                  Default                   
-----------+-------------+-----------+----------+--------------------------------------------
 id        | integer     |           | not null | nextval('cohere_vectors_id_seq'::regclass)
 embedding | vector(768) |           |          | 
Indexes:
    "cohere_vectors_pkey" PRIMARY KEY, btree (id)
    "cohere_vectors_diskann" diskann (embedding)
    "cohere_vectors_hnsw" hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='64')
    "cohere_vectors_ivfflat" ivfflat (embedding vector_cosine_ops) WITH (lists='1000')
    "cohere_vectors_vchordrq" vchordrq (embedding vector_l2_ops)
```

```
  python3 vector/query_hdf5.py --index-name "" --operator '<=>' --k 10
  python3 vector/query_hdf5.py --index-name cohere_vectors_ivfflat --operator '<=>' --k 10
  python3 vector/query_hdf5.py --index-name cohere_vectors_diskann --operator '<=>' --k 10
  python3 vector/query_hdf5.py --index-name cohere_vectors_hnsw --operator '<=>' --k 10
  python3 vector/query_hdf5.py --index-name cohere_vectors_vchordrq --operator '<->' --k 10
```

## Rust build commands

   export SDKROOT=$(xcrun --sdk macosx --show-sdk-path) && \
   RUSTFLAGS="-C link-arg=-Wl,-undefined,dynamic_lookup" \
   cargo pgrx install --release --features pg18

  Breakdown of the command:
   * export SDKROOT=...: Points the compiler to the macOS SDK headers (fixing the inttypes.h not found error).
   * RUSTFLAGS="-C link-arg=-Wl,-undefined,dynamic_lookup": Tells the linker to allow undefined symbols at build time, which will be resolved by the PostgreSQL process
     at runtime (fixing the Undefined symbols linker errors on macOS).
   * cargo pgrx install --release --features pg18: Compiles the extension in release mode specifically for PostgreSQL 18 and installs the artifacts to your ~/pgsql
     directory.

   export SDKROOT=$(xcrun --sdk macosx --show-sdk-path) && \
   PG_CONFIG=~/pgsql/bin/pg_config make && \
   make install

## Packages

icu4c@78 is keg-only, which means it was not symlinked into /opt/homebrew,
because macOS provides libicucore.dylib (but nothing else).

If you need to have icu4c@78 first in your PATH, run:
  echo 'export PATH="/opt/homebrew/opt/icu4c@78/bin:$PATH"' >> /Users/zedware/.bash_profile
  echo 'export PATH="/opt/homebrew/opt/icu4c@78/sbin:$PATH"' >> /Users/zedware/.bash_profile

For compilers to find icu4c@78 you may need to set:
  export LDFLAGS="-L/opt/homebrew/opt/icu4c@78/lib"
  export CPPFLAGS="-I/opt/homebrew/opt/icu4c@78/include"

##

postgres=# show maintenance_work_mem;
 maintenance_work_mem 
----------------------
 64MB
(1 row)

postgres=# CREATE INDEX ON cohere_vectors USING vchordrq (embedding vector_l2_ops);
INFO:  maintain: number_of_formerly_allocated_pages = 21
INFO:  maintain: number_of_formerly_allocated_pages = 0
INFO:  maintain: number_of_freshly_allocated_pages = 0
INFO:  maintain: number_of_freed_pages = 0
INFO:  maintain: number_of_formerly_allocated_pages = 0
INFO:  maintain: number_of_freshly_allocated_pages = 0
INFO:  maintain: number_of_freed_pages = 0
INFO:  maintain: number_of_formerly_allocated_pages = 0
INFO:  maintain: number_of_freshly_allocated_pages = 0
INFO:  maintain: number_of_freed_pages = 0
INFO:  maintain: number_of_formerly_allocated_pages = 0
INFO:  maintain: number_of_freshly_allocated_pages = 0
INFO:  maintain: number_of_freed_pages = 0
INFO:  maintain: number_of_freshly_allocated_pages = 16437
INFO:  maintain: number_of_freed_pages = 18184
CREATE INDEX
Time: 35863.743 ms (00:35.864)

postgres=# set maintenance_work_mem = '8GB';

postgres=# CREATE INDEX cohere_vectors_idx2 ON cohere_vectors USING diskann (embedding vector_cosine_ops);
NOTICE:  Starting index build with num_neighbors=-1, search_list_size=100, max_alpha=1.2, storage_layout=SbqCompression.
NOTICE:  Indexed 1000000 tuples
CREATE INDEX
Time: 1355890.062 ms (22:35.890)
