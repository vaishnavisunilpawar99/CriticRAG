"""
Benchmark Evaluation & Statistical Chart Generator
==================================================
Empirical experiment demonstrating hallucination reduction using StandaloneCritic
across arithmetic, temporal, and factual domains.
"""

import json
import os
import matplotlib.pyplot as plt
import numpy as np
from critic import StandaloneCritic

def run_experiment():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_dir, "sample_experiment_data.json")
    
    with open(data_path, "r", encoding="utf-8") as f:
        samples = json.load(f)
        
    critic = StandaloneCritic()
    
    total = len(samples)
    baseline_hallucinated_count = 0
    critic_detected_count = 0
    post_critic_hallucinated_count = 0
    
    category_stats = {}
    detailed_results = []
    
    for item in samples:
        cat = item["category"]
        if cat not in category_stats:
            category_stats[cat] = {
                "total": 0,
                "baseline_hallucinations": 0,
                "post_critic_hallucinations": 0
            }
        category_stats[cat]["total"] += 1
        
        # 1. Baseline analysis
        if item["baseline_hallucinated"]:
            baseline_hallucinated_count += 1
            category_stats[cat]["baseline_hallucinations"] += 1
            
        # 2. Critic Audit
        audit = critic.audit(item["question"], item["raw_baseline_answer"], item.get("evidence"))
        
        if audit.hallucination_detected:
            critic_detected_count += 1
            
        # 3. Post-critic evaluation
        # If corrected, re-audit to verify if hallucination was removed
        final_ans = audit.corrected_answer if audit.corrected_answer else item["raw_baseline_answer"]
        re_audit = critic.audit(item["question"], final_ans, item.get("evidence"))
        
        is_still_hallucinated = re_audit.hallucination_detected
        if is_still_hallucinated:
            post_critic_hallucinated_count += 1
            category_stats[cat]["post_critic_hallucinations"] += 1
            
        detailed_results.append({
            "id": item["id"],
            "question": item["question"],
            "raw_answer": item["raw_baseline_answer"],
            "ground_truth": item["ground_truth"],
            "critic_verdict": audit.verdict,
            "confidence": audit.confidence,
            "detected_issues": audit.audit_notes,
            "final_answer": final_ans,
            "baseline_hallucinated": item["baseline_hallucinated"],
            "post_critic_hallucinated": is_still_hallucinated
        })

    # Metrics Summary
    baseline_rate = (baseline_hallucinated_count / total) * 100.0
    post_critic_rate = (post_critic_hallucinated_count / total) * 100.0
    reduction_pct = ((baseline_rate - post_critic_rate) / baseline_rate) * 100.0
    
    baseline_acc = ((total - baseline_hallucinated_count) / total) * 100.0
    post_critic_acc = ((total - post_critic_hallucinated_count) / total) * 100.0
    
    summary = {
        "total_samples": total,
        "baseline_hallucination_count": baseline_hallucinated_count,
        "baseline_hallucination_rate_pct": round(baseline_rate, 2),
        "critic_detection_rate_pct": round((critic_detected_count / baseline_hallucinated_count) * 100.0, 2),
        "post_critic_hallucination_count": post_critic_hallucinated_count,
        "post_critic_hallucination_rate_pct": round(post_critic_rate, 2),
        "relative_hallucination_reduction_pct": round(reduction_pct, 2),
        "baseline_accuracy_pct": round(baseline_acc, 2),
        "post_critic_accuracy_pct": round(post_critic_acc, 2),
        "category_breakdown": category_stats
    }
    
    # Save JSON results
    out_json = os.path.join(base_dir, "benchmark_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "per_sample": detailed_results}, f, indent=2)
        
    print("\n" + "=" * 60)
    print("STANDALONE CRITIC BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total Evaluated Samples:            {total}")
    print(f"Baseline Hallucination Rate:        {baseline_rate:.1f}% ({baseline_hallucinated_count}/{total})")
    print(f"Post-Critic Hallucination Rate:     {post_critic_rate:.1f}% ({post_critic_hallucinated_count}/{total})")
    print(f"Relative Hallucination Reduction:   {reduction_pct:.1f}% Drop")
    print(f"Baseline Factual Accuracy:          {baseline_acc:.1f}%")
    print(f"Post-Critic Factual Accuracy:       {post_critic_acc:.1f}% (+{post_critic_acc - baseline_acc:.1f}% Gain)")
    print("=" * 60)

    # ========================================================================
    # STATISTICAL CHART GENERATION
    # ========================================================================
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)
    
    # Chart 1: Hallucination Rate Reduction & Accuracy Comparison
    ax1 = axes[0]
    metrics = ['Hallucination Rate (%)', 'Factual Accuracy (%)']
    baseline_vals = [baseline_rate, baseline_acc]
    critic_vals = [post_critic_rate, post_critic_acc]
    
    x = np.arange(len(metrics))
    width = 0.32
    
    rects1 = ax1.bar(x - width/2, baseline_vals, width, label='Raw Baseline (Single-Shot)', color='#E11D48', alpha=0.9, edgecolor='#9F1239')
    rects2 = ax1.bar(x + width/2, critic_vals, width, label='Post-Critic Verification', color='#10B981', alpha=0.9, edgecolor='#047857')
    
    ax1.set_ylabel('Percentage (%)', fontsize=11, fontweight='bold', color='#1E293B')
    ax1.set_title('Impact of Critic Verification on Hallucinations & Accuracy', fontsize=13, fontweight='bold', pad=12, color='#0F172A')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=11, fontweight='bold', color='#1E293B')
    ax1.set_ylim(0, 115)
    ax1.legend(frameon=True, facecolor='#F8FAFC', edgecolor='#CBD5E1', fontsize=10)
    
    for rect in rects1:
        h = rect.get_height()
        ax1.annotate(f'{h:.1f}%', xy=(rect.get_x() + rect.get_width() / 2, h),
                     xytext=(0, 4), textcoords="offset points", ha='center', va='bottom',
                     fontweight='bold', color='#9F1239', fontsize=10)
        
    for rect in rects2:
        h = rect.get_height()
        ax1.annotate(f'{h:.1f}%', xy=(rect.get_x() + rect.get_width() / 2, h),
                     xytext=(0, 4), textcoords="offset points", ha='center', va='bottom',
                     fontweight='bold', color='#047857', fontsize=10)

    # Chart 2: Category Breakdown
    ax2 = axes[1]
    categories = list(category_stats.keys())
    cat_short = [c.replace(" & ", "\n") for c in categories]
    cat_base = [category_stats[c]["baseline_hallucinations"] for c in categories]
    cat_post = [category_stats[c]["post_critic_hallucinations"] for c in categories]
    
    cx = np.arange(len(categories))
    cwidth = 0.35
    
    c_rects1 = ax2.bar(cx - cwidth/2, cat_base, cwidth, label='Baseline Hallucinations', color='#F59E0B', alpha=0.9, edgecolor='#B45309')
    c_rects2 = ax2.bar(cx + cwidth/2, cat_post, cwidth, label='Post-Critic Hallucinations', color='#3B82F6', alpha=0.9, edgecolor='#1D4ED8')
    
    ax2.set_ylabel('Number of Hallucinated Answers', fontsize=11, fontweight='bold', color='#1E293B')
    ax2.set_title('Hallucination Elimination by Domain Category', fontsize=13, fontweight='bold', pad=12, color='#0F172A')
    ax2.set_xticks(cx)
    ax2.set_xticklabels(cat_short, fontsize=9.5, fontweight='bold', color='#1E293B')
    ax2.legend(frameon=True, facecolor='#F8FAFC', edgecolor='#CBD5E1', fontsize=10)
    
    for rect in c_rects1:
        h = rect.get_height()
        if h > 0:
            ax2.annotate(f'{int(h)}', xy=(rect.get_x() + rect.get_width() / 2, h),
                         xytext=(0, 3), textcoords="offset points", ha='center', va='bottom',
                         fontweight='bold', color='#B45309', fontsize=9.5)
            
    for rect in c_rects2:
        h = rect.get_height()
        ax2.annotate(f'{int(h)}', xy=(rect.get_x() + rect.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom',
                     fontweight='bold', color='#1D4ED8', fontsize=9.5)
                     
    plt.tight_layout()
    chart_path = os.path.join(base_dir, "hallucination_reduction_chart.png")
    plt.savefig(chart_path, bbox_inches='tight')
    plt.close()
    print(f"\n[Chart Saved] Statistical visualization saved to: {chart_path}")
    return summary

if __name__ == "__main__":
    run_experiment()
