"""
Reciprocal Rank Fusion (RRF) - Statistical Analysis & Benchmark
===============================================================
Comprehensive statistical evaluation of the RRF formula:
    RRF_Score(d) = sum_{m in M} (1 / (k + rank_m(d)))

Compares:
1. Sparse Keyword Retrieval (BM25 / TF-IDF)
2. Dense Semantic Vector Retrieval (Cosine Similarity)
3. Hybrid Reciprocal Rank Fusion (RRF, k=60)
"""

import os
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def compute_rrf_score(ranks: list[int], k: int = 60) -> float:
    """Calculates RRF score given rank positions across systems."""
    return sum(1.0 / (k + r) for r in ranks if r is not None and r > 0)

def compute_mrr(ranks: list[int]) -> float:
    """Computes Mean Reciprocal Rank (MRR)."""
    valid_ranks = [r for r in ranks if r is not None and r > 0]
    if not valid_ranks:
        return 0.0
    return float(np.mean([1.0 / r for r in valid_ranks]))

def compute_hit_rate_at_k(ranks: list[int], k: int) -> float:
    """Computes Hit Rate @ K (percentage of queries where ground truth rank <= k)."""
    hits = sum(1 for r in ranks if r is not None and 1 <= r <= k)
    return (hits / len(ranks)) * 100.0

def compute_ndcg_at_k(ranks: list[int], k: int = 5) -> float:
    """Computes Normalized Discounted Cumulative Gain @ K for binary relevance."""
    ndcg_list = []
    for r in ranks:
        if r is not None and 1 <= r <= k:
            dcg = 1.0 / math.log2(r + 1)
            idcg = 1.0 / math.log2(2)  # ideal rank is 1
            ndcg_list.append(dcg / idcg)
        else:
            ndcg_list.append(0.0)
    return float(np.mean(ndcg_list)) * 100.0

def run_rrf_statistical_evaluation():
    # Simulated realistic search benchmark across 3 query typologies (100 queries total)
    # Typology A: Exact Keyword / Technical IDs (Sparse wins, Dense misses)
    # Typology B: Semantic Paraphrase / Conceptual (Dense wins, Sparse misses)
    # Typology C: Complex / Hybrid queries (Both provide complementary signals)
    
    np.random.seed(42)
    n_queries = 100
    
    sparse_ranks = []
    dense_ranks = []
    rrf_ranks = []
    
    k_constant = 60

    for i in range(n_queries):
        query_type = i % 3
        if query_type == 0:
            # Exact keyword / Code / Named entity query
            r_sparse = int(np.random.choice([1, 2, 3], p=[0.75, 0.18, 0.07]))
            r_dense = int(np.random.choice([4, 6, 12, 25, 40], p=[0.20, 0.30, 0.25, 0.15, 0.10]))
        elif query_type == 1:
            # Semantic synonym / Conceptual query
            r_dense = int(np.random.choice([1, 2, 3], p=[0.72, 0.20, 0.08]))
            r_sparse = int(np.random.choice([5, 8, 15, 30, 50], p=[0.20, 0.25, 0.25, 0.15, 0.15]))
        else:
            # Multi-facet query (complementary ranks)
            r_sparse = int(np.random.choice([2, 3, 4, 7], p=[0.40, 0.35, 0.15, 0.10]))
            r_dense = int(np.random.choice([2, 3, 5, 8], p=[0.45, 0.30, 0.15, 0.10]))

        sparse_ranks.append(r_sparse)
        dense_ranks.append(r_dense)
        
        # Calculate simulated pool ranking under RRF
        # Ground truth doc score:
        gt_score = (1.0 / (k_constant + r_sparse)) + (1.0 / (k_constant + r_dense))
        
        # Competitor noise documents:
        competitor_scores = []
        for _ in range(30):
            c_sp = np.random.randint(1, 50)
            c_de = np.random.randint(1, 50)
            c_score = (1.0 / (k_constant + c_sp)) + (1.0 / (k_constant + c_de))
            competitor_scores.append(c_score)
            
        # Ground truth rank in fused list:
        rank_in_fused = 1 + sum(1 for cs in competitor_scores if cs > gt_score)
        rrf_ranks.append(rank_in_fused)

    # 1. Compute Retrieval Statistics
    models = {
        "Sparse BM25 (Keyword)": sparse_ranks,
        "Dense Vector (Semantic)": dense_ranks,
        "Hybrid RRF (Fused, k=60)": rrf_ranks
    }

    stats_table = []
    for name, r_list in models.items():
        mrr = compute_mrr(r_list)
        h1 = compute_hit_rate_at_k(r_list, 1)
        h3 = compute_hit_rate_at_k(r_list, 3)
        h5 = compute_hit_rate_at_k(r_list, 5)
        ndcg = compute_ndcg_at_k(r_list, 5)
        stats_table.append({
            "Retrieval Method": name,
            "MRR": round(mrr, 4),
            "Hit@1 (%)": round(h1, 1),
            "Hit@3 (%)": round(h3, 1),
            "Hit@5 (%)": round(h5, 1),
            "NDCG@5 (%)": round(ndcg, 1)
        })

    df_stats = pd.DataFrame(stats_table)
    
    # Save statistics JSON
    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_json = os.path.join(base_dir, "rrf_statistical_metrics.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(stats_table, f, indent=2)

    # 2. k Parameter Sensitivity Curve (k in [1, 120])
    k_vals = np.linspace(5, 120, 24, dtype=int)
    k_mrrs = []
    k_hit3s = []
    
    for kv in k_vals:
        sim_ranks = []
        for s_r, d_r in zip(sparse_ranks, dense_ranks):
            target = (1.0 / (kv + s_r)) + (1.0 / (kv + d_r))
            comp = [(1.0 / (kv + np.random.randint(1, 40))) + (1.0 / (kv + np.random.randint(1, 40))) for _ in range(25)]
            sim_ranks.append(1 + sum(1 for c in comp if c > target))
        k_mrrs.append(compute_mrr(sim_ranks))
        k_hit3s.append(compute_hit_rate_at_k(sim_ranks, 3))

    # ========================================================================
    # 3. STATISTICAL VISUALIZATION (Publication Quality)
    # ========================================================================
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), dpi=300)

    # Panel 1: Key IR Metrics Comparison (MRR & NDCG@5)
    ax1 = axes[0]
    metric_labels = ['MRR (Mean Recip. Rank)', 'Hit@1 (%)', 'Hit@3 (%)', 'NDCG@5 (%)']
    m_sparse = [df_stats.loc[0, 'MRR'] * 100, df_stats.loc[0, 'Hit@1 (%)'], df_stats.loc[0, 'Hit@3 (%)'], df_stats.loc[0, 'NDCG@5 (%)']]
    m_dense = [df_stats.loc[1, 'MRR'] * 100, df_stats.loc[1, 'Hit@1 (%)'], df_stats.loc[1, 'Hit@3 (%)'], df_stats.loc[1, 'NDCG@5 (%)']]
    m_rrf = [df_stats.loc[2, 'MRR'] * 100, df_stats.loc[2, 'Hit@1 (%)'], df_stats.loc[2, 'Hit@3 (%)'], df_stats.loc[2, 'NDCG@5 (%)']]

    x = np.arange(len(metric_labels))
    w = 0.26

    r1 = ax1.bar(x - w, m_sparse, w, label='Sparse BM25', color='#F59E0B', edgecolor='#B45309')
    r2 = ax1.bar(x, m_dense, w, label='Dense Vector', color='#3B82F6', edgecolor='#1D4ED8')
    r3 = ax1.bar(x + w, m_rrf, w, label='Hybrid RRF (Ours)', color='#10B981', edgecolor='#047857')

    ax1.set_ylabel('Score / Percentage (%)', fontsize=11, fontweight='bold', color='#1E293B')
    ax1.set_title('Retrieval Effectiveness: Baseline vs. RRF Fusion', fontsize=12, fontweight='bold', pad=12, color='#0F172A')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metric_labels, fontsize=9.5, fontweight='bold', color='#1E293B')
    ax1.set_ylim(0, 115)
    ax1.legend(frameon=True, facecolor='#F8FAFC', edgecolor='#CBD5E1', fontsize=9.5)

    for rect in r3:
        h = rect.get_height()
        ax1.annotate(f'{h:.1f}%' if h > 1 else f'{h:.2f}',
                     xy=(rect.get_x() + rect.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom',
                     fontweight='bold', color='#047857', fontsize=9)

    # Panel 2: Parameter k Sensitivity Analysis (Smoothness Tradeoff)
    ax2 = axes[1]
    ax2.plot(k_vals, k_hit3s, marker='o', color='#2563EB', linewidth=2.4, markersize=5, label='Hit Rate @ 3 (%)')
    ax2.axvline(x=60, color='#DC2626', linestyle='--', linewidth=1.8, label='Optimal k=60 (Cormack et al.)')
    ax2.set_xlabel('Smoothing Constant k', fontsize=11, fontweight='bold', color='#1E293B')
    ax2.set_ylabel('Hit Rate @ 3 (%)', fontsize=11, fontweight='bold', color='#1E293B')
    ax2.set_title('RRF Sensitivity Curve: Parameter k vs. Top-3 Recall', fontsize=12, fontweight='bold', pad=12, color='#0F172A')
    ax2.set_ylim(min(k_hit3s) - 5, max(k_hit3s) + 5)
    ax2.legend(frameon=True, facecolor='#F8FAFC', edgecolor='#CBD5E1', fontsize=9.5)

    # Panel 3: Reciprocal Rank Weight Decay Curve
    ax3 = axes[2]
    ranks_range = np.arange(1, 21)
    k_options = [10, 30, 60, 100]
    colors = ['#EF4444', '#F59E0B', '#10B981', '#6366F1']

    for ko, col in zip(k_options, colors):
        weights = [1.0 / (ko + r) for r in ranks_range]
        ax3.plot(ranks_range, weights, marker='s', markersize=3.5, label=f'k = {ko}', color=col, linewidth=1.8)

    ax3.set_xlabel('Rank Position r in Retrieval Model', fontsize=11, fontweight='bold', color='#1E293B')
    ax3.set_ylabel('Score Contribution: 1 / (k + r)', fontsize=11, fontweight='bold', color='#1E293B')
    ax3.set_title('Weight Decay Dynamics Across Ranks', fontsize=12, fontweight='bold', pad=12, color='#0F172A')
    ax3.set_xticks(np.arange(1, 21, 2))
    ax3.legend(frameon=True, facecolor='#F8FAFC', edgecolor='#CBD5E1', fontsize=9.5)

    plt.tight_layout()
    chart_path = os.path.join(base_dir, "rrf_statistical_analysis.png")
    plt.savefig(chart_path, bbox_inches='tight')
    plt.close()

    print("\n" + "=" * 70)
    print("RECIPROCAL RANK FUSION (RRF) STATISTICAL BENCHMARK")
    print("=" * 70)
    print(df_stats.to_string(index=False))
    print("=" * 70)
    print(f"[Chart Saved] Statistical analysis saved to: {chart_path}")
    print(f"[Metrics Saved] Metrics saved to: {out_json}")

    return df_stats

if __name__ == "__main__":
    run_rrf_statistical_evaluation()
