import requests
import os
import re

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = "thomassolcia"

HEADERS = {"Authorization": f"bearer {GITHUB_TOKEN}"}
API_URL = "https://api.github.com/graphql"

QUERY = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
      }
      commitContributionsByRepository(maxRepositories: 10) {
        repository {
          nameWithOwner
          url
          primaryLanguage {
            name
          }
        }
        contributions(first: 100) {
          totalCount
        }
      }
    }
  }
}
"""

def run_query(query, variables):
    response = requests.post(API_URL, json={"query": query, "variables": variables}, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Query failed: {response.status_code} - {response.text}")

def generate_stats_md(contribs):
    total_commits = contribs["contributionCalendar"]["totalContributions"]
    repo_data = []
    lang_counter = {}

    for repo in contribs["commitContributionsByRepository"]:
        repo_name = repo["repository"]["nameWithOwner"]
        repo_url = repo["repository"]["url"]
        total_count = repo["contributions"]["totalCount"]
        primary_lang = repo["repository"]["primaryLanguage"]
        lang = primary_lang["name"] if primary_lang else "Unknown"

        lang_counter.setdefault(lang, {'repos': 0, 'commits': 0})
        lang_counter[lang]['repos'] += 1
        lang_counter[lang]['commits'] += total_count

        repo_data.append({
            "name": repo_name,
            "url": repo_url,
            "commits": total_count
        })
        
    md = '<div align="center">\n'
    md += '<div style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center;">\n'

    # ---------- Top Repositórios ----------
    md += '<div>\n<h3>Repositórios mais contribuídos:</h3>\n<table>\n'
    md += "<thead>\n<tr><th>Repositório</th><th>Commits</th></tr>\n</thead>\n<tbody>\n"

    top_repos = sorted(repo_data, key=lambda x: x['commits'], reverse=True)[:10]
    for r in top_repos:
        md += f'<tr><td><a href="{r["url"]}">{r["name"]}</a></td><td>{r["commits"]}</td></tr>\n'

    md += "</tbody>\n</table>\n</div>\n"

    # ---------- Linguagens mais usadas ----------
    md += '<div>\n<h3>Linguagens mais usadas:</h3>\n<table>\n'
    md += "<thead>\n<tr><th>Linguagem</th><th>Repositórios</th><th>Commits</th></tr>\n</thead>\n<tbody>\n"

    for lang, data in sorted(lang_counter.items(), key=lambda x: x[1]['commits'], reverse=True):
        md += f"<tr><td>{lang}</td><td>{data['repos']}</td><td>{data['commits']}</td></tr>\n"

    md += "</tbody>\n</table>\n</div>\n</div>\n</div>\n\n"
    md += f"- **Total de commits (últimos 12 meses):** {total_commits}\n"
    md += f"- **Repositórios contribuídos:** {len(repo_data)}\n"

    return md

def update_readme(new_stats):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(
        r"<!--START_GITHUB_STATS-->.*?<!--END_GITHUB_STATS-->",
        f"<!--START_GITHUB_STATS-->\n{new_stats}\n<!--END_GITHUB_STATS-->",
        content,
        flags=re.DOTALL
    )

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_content)

def main():
    result = run_query(QUERY, {"username": USERNAME})
    contribs = result["data"]["user"]["contributionsCollection"]
    stats_md = generate_stats_md(contribs)
    update_readme(stats_md)

if __name__ == "__main__":
    main()
