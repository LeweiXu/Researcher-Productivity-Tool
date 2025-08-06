import requests
from bs4 import BeautifulSoup
import re

def fetch_profile_list(page=0):
    base_url = "https://research-repository.uwa.edu.au"
    url = f"{base_url}/en/persons/?page={page}"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    print(soup.title.string)

    profiles = []
    pattern = re.compile(r"^/en/persons/[^/]+$")  # matches '/en/persons/<something_no_slash>'

    # Find all <a> tags with href attribute
    for a in soup.find_all("a", href=True):
        href = a['href']
        if pattern.match(href):
            full_url = requests.compat.urljoin(base_url, href)
            name = a.get_text(strip=True)
            if name and full_url not in [p['url'] for p in profiles]:
                profiles.append({"name": name, "url": full_url})

    return profiles

def fetch_researcher_details(profile_url):
    resp = requests.get(profile_url)
    soup = BeautifulSoup(resp.text, "html.parser")
    h_idx = soup.select_one(".h-index-selector")  # placeholder
    # Find output list
    outputs = []
    for item in soup.select(".research-output-entry"):
        title = item.select_one(".title-selector").get_text(strip=True)
        year = item.select_one(".year-selector").get_text(strip=True)
        in_field = item.select_one(".publication-field").get_text(strip=True)
        journal = re.sub(r"In:\s*", "", in_field)
        outputs.append({"title": title, "year": year, "journal": journal})
    return {"h_index": h_idx and h_idx.get_text(strip=True), "outputs": outputs}

if __name__ == "__main__":
    profiles = fetch_profile_list(page=1)
    print(f"Found {len(profiles)} profiles on page 1")
    if profiles:
        print("First researcher:", profiles[0])
        details = fetch_researcher_details(profiles[0]['url'])
        print(f"H-index: {details['h_index']}")
        print(f"Number of outputs: {len(details['outputs'])}")
        if details['outputs']:
            print("First publication:", details['outputs'][0])