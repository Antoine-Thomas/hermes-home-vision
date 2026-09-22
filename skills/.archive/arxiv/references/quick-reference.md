# Quick Reference

| Action | Command |
|--------|---------|
| Search papers | `curl "https://export.arxiv.org/api/query?search_query=all:QUERY&max_results=5"` |
| Get specific paper | `curl "https://export.arxiv.org/api/query?id_list=2402.03300"` |
| Read abstract (web) | `web_extract(urls=["https://arxiv.org/abs/2402.03300"])` |
| Read full paper (PDF) | `web_extract(urls=["https://arxiv.org/pdf/2402.03300"])` |
