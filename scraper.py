import feedparser
import requests
import hashlib
import os
from bs4 import BeautifulSoup
from models import Opportunity
from typing import List

def fetch_reddit_opportunities(subreddits: List[str] = ['forhire', 'freelance', 'hackathon']) -> List[Opportunity]:
    """Scrapes recent opportunities from Reddit generic RSS feeds."""
    opportunities = []
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/new/.rss"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            response = requests.get(url, headers=headers)
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries:
                # Basic pre-filtering for hiring/opps
                title = entry.title.lower()
                if '[hiring]' in title or 'hackathon' in title or 'opportunity' in title or sub == 'hackathon':
                    soup = BeautifulSoup(entry.summary, 'html.parser')
                    text_desc = soup.get_text()
                    
                    opp = Opportunity(
                        id=f"reddit_{hashlib.md5(entry.link.encode()).hexdigest()[:12]}",
                        title=entry.title,
                        description=text_desc[:1000], # Keep reasonably short
                        url=entry.link,
                        source=f"Reddit: r/{sub}",
                        published_date=entry.get('published', 'Unknown')
                    )
                    opportunities.append(opp)
        except Exception as e:
            print(f"Error scraping Reddit {sub}: {str(e)}")
            
    return opportunities

def fetch_github_issues(topics: List[str] = ['freelance', 'hackathon', 'help-wanted'], limit: int = 15) -> List[Opportunity]:
    """Scrapes recent GitHub issues looking for help."""
    opportunities = []
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
        
    for topic in topics:
        url = f"https://api.github.com/search/issues?q=label:{topic}+state:open&sort=created&order=desc&per_page={limit}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('items', []):
                    # Filter out PRs
                    if 'pull_request' not in item:
                        opp = Opportunity(
                            id=f"gh_{item['id']}",
                            title=item['title'],
                            description=str(item.get('body', 'No description'))[:1000],
                            url=item['html_url'],
                            source="GitHub Issues",
                            published_date=item['created_at']
                        )
                        opportunities.append(opp)
        except Exception as e:
            print(f"Error scraping GitHub issues: {str(e)}")
            
    return opportunities

def run_all_scrapers() -> List[Opportunity]:
    """Runs all scrapers and aggregates the results."""
    all_opps = []
    all_opps.extend(fetch_reddit_opportunities())
    all_opps.extend(fetch_github_issues())
    return all_opps
