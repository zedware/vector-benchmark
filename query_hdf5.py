import argparse
import time
import os
import warnings
import webbrowser
import h5py
import psycopg2
import plotly.graph_objects as go

def main():
    parser = argparse.ArgumentParser(description="Query HDF5 vectors from PostgreSQL to calculate recall")
    parser.add_argument("--hdf5-path", "-f", default="/Users/zedware/Downloads/cohere-768-angular.hdf5", help="Path to HDF5 file")
    parser.add_argument("--db-url", "-d", default="postgres://localhost:5432/postgres", help="Database connection string")
    parser.add_argument("--table-name", "-t", default="cohere_vectors", help="Target table name")
    parser.add_argument("--num-queries", "-n", type=int, default=100, help="Number of queries to run")
    parser.add_argument("--k", "-k", dest="k", type=int, default=10, help="Number of top results to retrieve (k)")
    parser.add_argument("--operator", "-o", type=str, default="<=>", help="Vector distance operator (e.g., <=>, <->, <#>)")
    parser.add_argument("--index-name", "-i", type=str, default="", help="Force use of a specific index by name (only for --hint-method pg_hint_plan)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed query information per iterations")
    parser.add_argument("--plot", "-p", action="store_true", help="Generate and open an interactive HTML plot of execution times")
    parser.add_argument("--hint-method", "-m", choices=["native", "pg_hint_plan"], default="native", help="Method to force scan types (default: native)")
    args = parser.parse_args()

    if args.hint_method == "native" and args.index_name:
        warnings.warn("The --index-name argument cannot be used when --hint-method is 'native'.")

    print(f"Opening HDF5 file to generate query vectors: {args.hdf5_path}")
    with h5py.File(args.hdf5_path, 'r') as f:
        query_vectors = f['test'][:]       # 10,000 query vectors
        # Note: We no longer rely on f['neighbors'] for ground truth

    conn = psycopg2.connect(args.db_url)
    cur = conn.cursor()

    if args.hint_method == "pg_hint_plan":
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_hint_plan';")
        if not cur.fetchone():
            warnings.warn("The --hint-method 'pg_hint_plan' was selected, but the 'pg_hint_plan' extension does not appear to be installed on the server. "
                          "Hints will be ignored by the query planner unless the extension is active.")

    total_recall = 0.0
    total_seq_time = 0.0
    total_ann_time = 0.0

    seq_times = []
    ann_times = []

    print(f"Running {args.num_queries} queries to calculate Recall@{args.k} against database baseline using {args.hint_method} hints...")
    
    for i in range(args.num_queries):
        query_vec = query_vectors[i].tolist()
        
        # 1. Gather Ground Truth via forced SeqScan
        hint_seq = ""
        if args.hint_method == "native":
            # We disable index usage for this transaction to force a full sequential scan baseline
            cur.execute("SET LOCAL enable_indexscan = off;")
            cur.execute("SET LOCAL enable_bitmapscan = off;")
            cur.execute("SET LOCAL enable_indexonlyscan = off;")
        else:
            hint_seq = f"/*+ SeqScan({args.table_name}) */ "
        
        start_time_seq = time.perf_counter()
        cur.execute(f"""
            {hint_seq}SELECT id FROM {args.table_name} 
            ORDER BY embedding {args.operator} %s::vector 
            LIMIT %s
        """, (query_vec, args.k))
        seq_duration = time.perf_counter() - start_time_seq
        
        # We simply use the returned subset of IDs securely since both come out of Postgres identically
        true_neighbors = {row[0] for row in cur.fetchall()}
        if args.hint_method == "native":
            conn.commit() # End transaction to reset enable_* settings
        
        # 2. Query target ANN index
        hint_ann = ""
        if args.hint_method == "native":
            # We disable sequential scans to force usage of the available index
            if args.index_name:
                cur.execute("SET LOCAL enable_seqscan = off;")
        else:
            if args.index_name:
                hint_ann = f"/*+ Index({args.table_name} {args.index_name}) */ "
            else:
                hint_ann = f"/*+ SeqScan({args.table_name}) */ "

        start_time_ann = time.perf_counter()
        cur.execute(f"""
            {hint_ann}SELECT id FROM {args.table_name} 
            ORDER BY embedding {args.operator} %s::vector 
            LIMIT %s
        """, (query_vec, args.k))
        ann_duration = time.perf_counter() - start_time_ann
        
        retrieved_neighbors = {row[0] for row in cur.fetchall()}
        if args.hint_method == "native":
            conn.commit() # End transaction to reset enable_* settings
        
        if args.verbose:
            print(f"--- Query {i + 1}/{args.num_queries} ---")
            if cur.query:
                query_str = cur.query.decode('utf-8') if isinstance(cur.query, bytes) else cur.query
                vector_start = query_str.find("'[")
                vector_end = query_str.find("]'", vector_start) if vector_start != -1 else -1
                if vector_start != -1 and vector_end != -1:
                    query_str = query_str[:vector_start+15] + "...]'" + query_str[vector_end+2:]
                print(f"Executed latest Query: {query_str.strip()}")

            print(f"SeqScan Time: {seq_duration:.4f}s (Recall@{args.k} = 1.0000)")
            if args.index_name and args.hint_method == "pg_hint_plan":
                print(f"ANN Index ({args.index_name}) Time: {ann_duration:.4f}s (Recall@{args.k} = {recall:.4f})")
            else:
                print(f"ANN Index Time: {ann_duration:.4f}s (Recall@{args.k} = {recall:.4f})")

        # 3. Calculate match overlap 
        matches = len(true_neighbors.intersection(retrieved_neighbors))
        recall = matches / args.k
        total_recall += recall
        
        # Accumulate sums
        total_seq_time += seq_duration
        total_ann_time += ann_duration
        
        seq_times.append(seq_duration)
        ann_times.append(ann_duration)

    avg_recall = total_recall / args.num_queries
    avg_seq_time = total_seq_time / args.num_queries
    avg_ann_time = total_ann_time / args.num_queries
    
    print(f"--- Results ---")
    print(f"Average SeqScan Time: {avg_seq_time:.4f}s")
    print(f"Average ANN Index Time: {avg_ann_time:.4f}s")
    print(f"Average Recall@{args.k}: {avg_recall:.4f}")

    cur.close()
    conn.close()

    if args.plot:
        print("Generating interactive execution plot...")
        fig = go.Figure()
        queries = list(range(1, args.num_queries + 1))
        
        fig.add_trace(go.Scatter(x=queries, y=seq_times, mode='lines+markers', name='SeqScan Time', line=dict(color='red')))
        fig.add_trace(go.Scatter(x=queries, y=ann_times, mode='lines+markers', name='ANN Index Time', line=dict(color='blue')))
        
        fig.update_layout(
            title=f"Query Execution Times (n={args.num_queries})",
            xaxis_title="Query Iteration",
            yaxis_title="Time (seconds)",
            legend_title="Query Type",
            hovermode="x unified"
        )
        
        plot_path = os.path.abspath("vector_query_performance.html")
        fig.write_html(plot_path)
        print(f"Plot saved to: {plot_path}")
        webbrowser.open(f"file://{plot_path}")

if __name__ == "__main__":
    main()