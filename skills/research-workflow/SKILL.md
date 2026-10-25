---
name: research-workflow
description: "Academic research: search arXiv papers, write ML papers for top venues. Use when: arXiv, research paper, paper writing, NeurIPS, ICML, ICLR, academic, citation."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Papers, arXiv, Academic, Paper-Writing, ML, AI, NeurIPS, ICML, ICLR]
    related_skills: [llm-wiki, huggingface-hub]
---

# Research Workflow

Academic research pipeline — from paper discovery to publication-ready manuscripts.

## Section 1: arXiv Paper Search

Search and retrieve academic papers from arXiv via their free REST API. No API key needed.

### Quick Reference

| Action | Command |
|--------|---------|
| Search papers | `curl "https://export.arxiv.org/api/query?search_query=all:QUERY&max_results=5"` |
| Get specific paper | `curl "https://export.arxiv.org/api/query?id_list=2402.03300"` |
| Read abstract | `web_extract(urls=["https://arxiv.org/abs/2402.03300"])` |
| Read full paper | `web_extract(urls=["https://arxiv.org/pdf/2402.03300"])` |

### Search Query Syntax

| Prefix | Searches | Example |
|--------|----------|---------|
| `all:` | All fields | `all:transformer+attention` |
| `ti:` | Title | `ti:large+language+models` |
| `au:` | Author | `au:vaswani` |
| `cat:` | Category | `cat:cs.AI` |

### Boolean operators

```
search_query=all:GPT+OR+all:BERT           # OR
search_query=all:language+model+ANDNOT+all:vision  # AND NOT
search_query=ti:"chain+of+thought"          # Exact phrase
```

### Common Categories

| Category | Field |
|----------|-------|
| `cs.AI` | Artificial Intelligence |
| `cs.CL` | Computation and Language (NLP) |
| `cs.CV` | Computer Vision |
| `cs.LG` | Machine Learning |

### Helper Script

```bash
python scripts/search_arxiv.py "GRPO reinforcement learning"
python scripts/search_arxiv.py --author "Yann LeCun" --max 5
python scripts/search_arxiv.py --id 2402.03300
```

### Semantic Scholar (Citations)

```bash
# Get paper details + citations
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300?fields=title,citationCount"

# Get citations OF a paper
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300/citations?fields=title,year&limit=10"

# Search papers (returns JSON)
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=GRPO&fields=title,citationCount"
```

## Section 2: Research Paper Writing

End-to-end pipeline for producing publication-ready ML/AI research papers targeting NeurIPS, ICML, ICLR, ACL, AAAI, and COLM.

### Pipeline Overview

```
Literature Review → Experiment Design → Execution → Analysis → Writing → Review → Revision → Submission
```

This is NOT a linear pipeline — it's an iterative loop. Results trigger new experiments. Reviews trigger new analysis.

### Key Stages

1. **Literature Review** — Search arXiv, read papers, identify gaps
2. **Experiment Design** — Hypothesis, baselines, metrics, statistical power
3. **Execution** — Run experiments, monitor, log to W&B
4. **Analysis** — Statistical tests, visualization, ablation studies
5. **Writing** — LaTeX paper with proper structure
6. **Review** — Self-review, then external feedback
7. **Revision** — Address reviews, re-run experiments if needed
8. **Submission** — Format check, supplementary materials

### Paper Structure

```
Abstract (150-250 words)
1. Introduction (motivation, contribution list, paper outline)
2. Related Work (grouped by theme, honest comparison)
3. Method (formal problem statement, approach, algorithm)
4. Experiments (setup, baselines, results, ablation)
5. Discussion (limitations, broader impact)
6. Conclusion (summary, future work)
References
Appendix (proofs, additional experiments, hyperparameters)
```

### Statistical Rigor

- Report confidence intervals (95% CI)
- Run 3-5 seeds minimum
- Use paired t-test or Wilcoxon for comparisons
- Report effect sizes (Cohen's d)
- Bonferroni correction for multiple comparisons

### LaTeX Tips

```latex
\usepackage{neurips_2025}  % or icml2025, iclr2026
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{booktabs}  % for \toprule, \midrule, \bottomrule
```

---

## Complete Research Workflow

1. **Discover:** `python scripts/search_arxiv.py "your topic" --sort date`
2. **Assess impact:** Check citation count on Semantic Scholar
3. **Read:** `web_extract(urls=["https://arxiv.org/pdf/ID"])`
4. **Find related work:** Semantic Scholar references endpoint
5. **Design experiments:** Hypothesis, baselines, metrics
6. **Execute:** Run experiments, log to W&B
7. **Analyze:** Statistical tests, visualization
8. **Write:** LaTeX paper
9. **Review:** Self-review + external feedback
10. **Submit:** Format check, supplementary materials

## Common Pitfalls

1. **Not reading enough related work** — read 20+ papers before starting
2. **Weak baselines** — compare against SOTA, not just naive baselines
3. **No statistical rigor** — always report confidence intervals and seeds
4. **Cherry-picking results** — report all experiments, including failures
5. **Ignoring limitations** — reviewers will find them anyway
6. **Poor writing quality** — proofread, use Grammarly, get feedback
7. **Missing reproducibility** — include code, hyperparameters, seeds

## Verification Checklist

- [ ] Literature review covers 20+ relevant papers
- [ ] Experiments have 3-5 seeds with confidence intervals
- [ ] Statistical tests applied for comparisons
- [ ] Paper follows venue template exactly
- [ ] All figures are readable in grayscale
- [ ] References are complete and properly formatted
- [ ] Supplementary materials include code link
