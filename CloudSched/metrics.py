"""MEMBER: Piyush Gairola (Team Lead) -- Performance metrics + adaptive algorithm recommendation.
Computes waiting/turnaround/response time and CPU utilisation, then scores all algorithms."""
import algorithms

def summarize(jobs, algo):
    timeline, m = algorithms.simulate(jobs, algo); n = len(jobs)
    busy = sum(e - s for _, s, e in timeline)
    span = max(e for *_, e in timeline) - min(j["arrival"] for j in jobs)
    return {"algorithm": algo,
            "avg_wait": sum(x["wait"] for x in m.values()) / n,
            "avg_tat": sum(x["tat"] for x in m.values()) / n,
            "avg_resp": sum(x["resp"] for x in m.values()) / n,
            "cpu_util": round(100 * busy / span, 1), "timeline": timeline}

def compare(jobs, weights=(0.3, 0.3, 0.2, 0.2)):
    """Weighted score = w1*wait + w2*turnaround + w3*response + w4*(1-utilisation), each min-max normalised.
    Lowest score wins. Returns (all results, best algorithm name)."""
    results = [summarize(jobs, a) for a in ("FCFS", "SJF", "PRIORITY", "RR")]
    def norm(key, invert=False):
        v = [r[key] for r in results]; lo, hi = min(v), max(v)
        return [0 if hi == lo else ((hi - x) if invert else (x - lo)) / (hi - lo) for x in v]
    cols = [norm("avg_wait"), norm("avg_tat"), norm("avg_resp"), norm("cpu_util", invert=True)]
    for i, r in enumerate(results):
        r["score"] = round(sum(w * c[i] for w, c in zip(weights, cols)), 3)
    return results, min(results, key=lambda r: r["score"])["algorithm"]
