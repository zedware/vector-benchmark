import argparse
import io
import h5py
import psycopg2

def main():
    parser = argparse.ArgumentParser(description="Load HDF5 vectors into PostgreSQL")
    parser.add_argument("--hdf5-path", "-f", default="/Users/zedware/Downloads/cohere-768-angular.hdf5", help="Path to HDF5 file")
    parser.add_argument("--db-url", "-d", default="postgres://localhost:5432/postgres", help="Database connection string")
    parser.add_argument("--table-name", "-t", default="cohere_vectors", help="Target table name")
    parser.add_argument("--dimensions", "-D", type=int, default=768, help="Vector dimensions")
    parser.add_argument("--batch-size", "-b", type=int, default=10000, help="Batch size for insertion")
    args = parser.parse_args()

    print(f"Opening HDF5 file: {args.hdf5_path}")
    with h5py.File(args.hdf5_path, 'r') as f:
        train_data = f['train']
        num_vectors = train_data.shape[0]
        print(f"Found {num_vectors} vectors with dimension {train_data.shape[1]}")

        conn = psycopg2.connect(args.db_url)
        cur = conn.cursor()

        # Create table with pgvector
        print("Ensuring pgvector extension and table exist...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(f"CREATE TABLE IF NOT EXISTS {args.table_name} (id INT PRIMARY KEY, embedding vector({args.dimensions}));")
        conn.commit()
 
        # Get current count to resume
        cur.execute(f"SELECT count(*) FROM {args.table_name};")
        current_count = cur.fetchone()[0]
        print(f"Resuming from {current_count}...")
        
        # Use copy_expert for maximum performance
        # We'll stream data in batches to avoid memory issues
        for i in range(current_count, num_vectors, args.batch_size):
            end = min(i + args.batch_size, num_vectors)
            batch = train_data[i:end]
            
            # Prepare buffer for COPY
            output = io.StringIO()
            for idx, row in enumerate(batch):
                # Calculate the original ID (row index)
                row_id = i + idx
                # Format as postgres vector string: [v1,v2,...]
                vec_str = "[" + ",".join(map(str, row)) + "]"
                # Use tab separation for COPY (default)
                output.write(f"{row_id}\t{vec_str}\n")
            
            output.seek(0)
            cur.copy_from(output, args.table_name, columns=('id', 'embedding'))
            
            if end % 100000 == 0:
                print(f"Processed {end}/{num_vectors} vectors...")
                conn.commit()

        conn.commit()
        cur.close()
        conn.close()

    print("Migration completed successfully.")

if __name__ == "__main__":
    main()
