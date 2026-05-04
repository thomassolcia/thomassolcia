import os
import re
from collections import defaultdict

import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = "thomassolcia"

HEADERS = {"Authorization": f"bearer {GITHUB_TOKEN}"}
API_URL = "https://api.github.com/graphql"

QUERY = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            weekday
          }
        }
      }
      commitContributionsByRepository(maxRepositories: 100) {
        repository {
          nameWithOwner
          url
          isPrivate
          isFork
          owner { login }
          primaryLanguage { name }
        }
        contributions(first: 1) {
          totalCount
        }
      }
      pullRequestContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner owner { login } }
        contributions(first: 1) { totalCount }
      }
      issueContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner owner { login } }
        contributions(first: 1) { totalCount }
      }
    }
    pullRequests(states: OPEN, first: 1) { totalCount }
    issues(states: OPEN, first: 1) { totalCount }
  }
}
"""


def run_query(query, variables):
    r = requests.post(API_URL, json={"query": query, "variables": variables}, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data


def build_top_repos(repo_data):
    md = '<div>\n<h3>Repositórios mais contribuídos:</h3>\n<table>\n'
    md += "<thead>\n<tr><th>Repositório</th><th>Owner</th><th>Commits</th></tr>\n</thead>\n<tbody>\n"
    for r in sorted(repo_data, key=lambda x: x["commits"], reverse=True)[:10]:
        own = "you" if r["owner"].lower() == USERNAME.lower() else r["owner"]
        priv = " 🔒" if r["private"] else ""
        fork = " 🍴" if r["fork"] else ""
        md += f'<tr><td><a href="{r["url"]}">{r["name"]}</a>{priv}{fork}</td><td>{own}</td><td>{r["commits"]}</td></tr>\n'
    md += "</tbody>\n</table>\n</div>\n"
    return md


def build_languages(lang_counter):
    md = '<div>\n<h3>Linguagens mais usadas:</h3>\n<table>\n'
    md += "<thead>\n<tr><th>Linguagem</th><th>Repositórios</th><th>Commits</th></tr>\n</thead>\n<tbody>\n"
    for lang, d in sorted(lang_counter.items(), key=lambda x: x[1]["commits"], reverse=True):
        md += f"<tr><td>{lang}</td><td>{d['repos']}</td><td>{d['commits']}</td></tr>\n"
    md += "</tbody>\n</table>\n</div>\n"
    return md


def build_orgs(org_counter):
    if not org_counter:
        return ""
    md = '<div>\n<h3>Contribuições por owner / organização:</h3>\n<table>\n'
    md += "<thead>\n<tr><th>Owner</th><th>Repositórios</th><th>Commits</th></tr>\n</thead>\n<tbody>\n"
    for owner, d in sorted(org_counter.items(), key=lambda x: x[1]["commits"], reverse=True):
        label = "you" if owner.lower() == USERNAME.lower() else owner
        md += f"<tr><td>{label}</td><td>{d['repos']}</td><td>{d['commits']}</td></tr>\n"
    md += "</tbody>\n</table>\n</div>\n"
    return md


def build_activity(weeks):
    by_dow = defaultdict(int)
    dow_names = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
    streak = best_streak = 0
    days_flat = []
    for w in weeks:
        for d in w["contributionDays"]:
            by_dow[d["weekday"]] += d["contributionCount"]
            days_flat.append(d["contributionCount"])
    for c in days_flat:
        if c > 0:
            streak += 1
            best_streak = max(best_streak, streak)
        else:
            streak = 0
    current = 0
    for c in reversed(days_flat):
        if c > 0:
            current += 1
        else:
            break

    md = '<div>\n<h3>Padrão de atividade (últimos 12 meses):</h3>\n<table>\n'
    md += "<thead>\n<tr><th>Dia</th><th>Contribuições</th></tr>\n</thead>\n<tbody>\n"
    for i in range(7):
        md += f"<tr><td>{dow_names[i]}</td><td>{by_dow[i]}</td></tr>\n"
    md += "</tbody>\n</table>\n</div>\n"
    return md, current, best_streak


def generate_stats_md(user):
    contribs = user["contributionsCollection"]
    repo_data = []
    lang_counter = {}
    org_counter = defaultdict(lambda: {"repos": 0, "commits": 0})

    for repo in contribs["commitContributionsByRepository"]:
        rp = repo["repository"]
        count = repo["contributions"]["totalCount"]
        owner = rp["owner"]["login"]
        lang = rp["primaryLanguage"]["name"] if rp["primaryLanguage"] else "Unknown"

        lang_counter.setdefault(lang, {"repos": 0, "commits": 0})
        lang_counter[lang]["repos"] += 1
        lang_counter[lang]["commits"] += count

        org_counter[owner]["repos"] += 1
        org_counter[owner]["commits"] += count

        repo_data.append({
            "name": rp["nameWithOwner"],
            "url": rp["url"],
            "owner": owner,
            "commits": count,
            "private": rp["isPrivate"],
            "fork": rp["isFork"],
        })

    activity_md, current_streak, best_streak = build_activity(
        contribs["contributionCalendar"]["weeks"]
    )

    md = '<div align="center">\n'
    md += '<div style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center;">\n'
    md += build_top_repos(repo_data)
    md += build_languages(lang_counter)
    md += build_orgs(org_counter)
    md += activity_md
    md += "</div>\n</div>\n\n"

    total_calendar = contribs["contributionCalendar"]["totalContributions"]
    external_repos = sum(1 for r in repo_data if r["owner"].lower() != USERNAME.lower())
    private_repos = sum(1 for r in repo_data if r["private"])

    md += f"- **Total de contribuições (12 meses):** {total_calendar}\n"
    md += f"- **Commits:** {contribs['totalCommitContributions']} · **PRs:** {contribs['totalPullRequestContributions']} · **Issues:** {contribs['totalIssueContributions']} · **Reviews:** {contribs['totalPullRequestReviewContributions']}\n"
    md += f"- **Repositórios contribuídos:** {len(repo_data)} (próprios: {len(repo_data) - external_repos} · de terceiros: {external_repos} · privados: {private_repos})\n"
    md += f"- **Contribuições restritas/privadas (calendário):** {contribs['restrictedContributionsCount']}\n"
    md += f"- **Streak atual:** {current_streak} dias · **maior streak (12m):** {best_streak} dias\n"
    md += f"- **PRs abertos:** {user['pullRequests']['totalCount']} · **Issues abertas:** {user['issues']['totalCount']}\n"
    return md


def update_readme(new_stats):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(
        r"<!--START_GITHUB_STATS-->.*?<!--END_GITHUB_STATS-->",
        f"<!--START_GITHUB_STATS-->\n{new_stats}\n<!--END_GITHUB_STATS-->",
        content,
        flags=re.DOTALL,
    )
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_content)


def main():
    result = run_query(QUERY, {"username": USERNAME})
    stats_md = generate_stats_md(result["data"]["user"])
    update_readme(stats_md)


if __name__ == "__main__":
    main()
