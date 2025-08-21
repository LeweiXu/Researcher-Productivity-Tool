from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import csv
import re
from pyalex import Works, Authors, Institutions


# ---------------- OpenAlex Helpers ----------------
def get_author_id(name):
    try:
        authors = Authors().search(name).get()
        if authors:
            author_id = authors[0]["id"]
            # Extract just the ID part if needed
            if author_id.startswith("https://openalex.org/"):
                return author_id.split("/")[-1]
        return None
    except Exception as e:
        print("Author lookup error:", e)
        return None
    
def clean_name(name):
    # Remove common academic and honorific titles from the start of the name
    return re.sub(
        r"^(Professor |Prof\.? |Associate Professor |A/Prof |Adjunct |Emeritus Professor |Scientia Professor |Dr |Mr |Mrs |Ms )",
        "",
        name,
        flags=re.IGNORECASE
    ).strip()

def get_ins_id(ins_name):
    try:
        insts = Institutions().search(ins_name).get()
        if insts:
            inst_id = insts[0]["id"]
            if inst_id.startswith("https://openalex.org/"):
                return inst_id.split("/")[-1]
        return None
    except Exception as e:
        print("Institution lookup error:", e)
        return None

def clean_title(title):
    # Remove all unwanted characters from the title
    return re.sub(r"[\"'“”‘’:]", "", title)

def openAlex(title, year, author_id = None, institution_id = None):
    title = clean_title(title)
    try:
        # Convert year to yyyy-mm-dd
        if year and year.isdigit() and len(year) == 4:
            from_date = f"{year}-01-01"
            to_date = f"{year}-12-31"
        else:
            from_date = None
            to_date = None

        query = Works().search(title)
        if from_date and to_date:
            query = query.filter(
                from_publication_date=from_date,
                to_publication_date=to_date
            )

        if author_id:
            query = query.filter(author={"id": author_id})
        if institution_id:
            query = query.filter(institution={"id": institution_id})

        results = query.get()
        
        if results:
            # Get the OpenAlex ID and convert to a direct link
            openalex_id = results[0]["id"]
            if openalex_id.startswith("https://openalex.org/"):
                return openalex_id
            # If it's an API URL, extract the ID and build the link
            match = re.search(r'W\d+', openalex_id)
            if match:
                return f"https://openalex.org/{match.group(0)}"
        else:
            return f"https://www.google.com/search?q={title}"
    except Exception as e:
        print("Error:", e)
        return ""


# ---------------- Scraping Function ----------------
def scraping(profile_url, driver):
    driver.get(profile_url)
    time.sleep(1)

    publications_info = []

    # Map section keywords to article types
    sections = {
        "Journal Articles": "Journal",
        "Other": "",
        "Book Chapters": "",
        "Books": "",
        "Working Papers": "",
        "Edited Books": ""
    }

    buttons = driver.find_elements(By.CSS_SELECTOR, "button.accordion-item")

    # Researcher name
    try:
        name = driver.find_element(By.CSS_SELECTOR, "h1.profile-heading").text.strip()
    except Exception:
        name = ""

    # Author ID & Institution ID for OpenAlex to look up
    author_id = get_author_id(clean_name(name))
    institution_id = get_ins_id("UNSW Sydney")

    for btn in buttons:
        for section, default_article_type in sections.items():
            if section in btn.text:
                if btn.get_attribute("aria-expanded") == "false":
                    btn.click()
                    time.sleep(3)  # Wait for the section to expand
                # Only get publications under the currently expanded section
                section_div = btn.find_element(By.XPATH, "./following-sibling::div")
                publications = section_div.find_elements(By.CSS_SELECTOR, "div.publication-item")

                for pub in publications:
                    # Title
                    try:
                        if section == "Books":
                            title = pub.find_element(By.CSS_SELECTOR, "i.rg-title").text.strip()
                        else:
                            title = pub.find_element(By.CSS_SELECTOR, "span.rg-title").text.strip()
                        # Remove ' and " only at the start and end
                        title = title.strip("'\"")
                    except Exception:
                        title = ""
                    # Skip empty publication items
                    if not title:
                        continue
                    
                    # Year
                    try:
                        year = pub.find_element(By.CSS_SELECTOR, "span.rg-year").text.strip()
                    except Exception:
                        year = "N/A"

                    # Article Type
                    try:
                        article_type = pub.find_element(By.CSS_SELECTOR, "span.publication-category").text.strip()
                    except Exception:
                        article_type = ""

                    # Journal name
                    if article_type and "journal" in article_type.lower():
                        try:
                            journal = pub.find_element(By.CSS_SELECTOR, "i.rg-source-title").text.strip()
                        except Exception:
                            journal = ""
                    else:
                        journal = ""

                    # Article URL
                    try:
                        pub_url = pub.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                    except Exception:
                        pub_url = ""

                    # If missing, check OpenAlex
                    if not pub_url and title:
                        pub_url = openAlex(title, year, author_id, institution_id)

                    publications_info.append([title, year, article_type, journal, pub_url])
                    print(f"Found publication: {title} ({article_type})")
                break
    return name, publications_info


# ---------------- Profile Scraping ----------------
def profile(page_url, driver):
    driver.get(page_url)
    time.sleep(2)

    profile_urls = []

    profile_link = driver.find_elements(By.CSS_SELECTOR, "a.card-profile__container")
    for e in profile_link:
        url = e.get_attribute("href")
        if url:
            profile_urls.append(url)

    return profile_urls


# ---------------- Main Function ----------------
def scrape_UNSW():
    # start_time = time.time()  # Start timer for testing purpose

    driver = webdriver.Chrome()
    departments_urls = [
        "https://www.unsw.edu.au/business/our-people#search=&filters=f.School%257CstaffSchool%3ASchool%2Bof%2BAccounting%252C%2BAuditing%2Band%2BTaxation&sort=metastaffLastName",
        "https://www.unsw.edu.au/business/our-people#search=&filters=f.School%257CstaffSchool%3ASchool%2Bof%2BBanking%2Band%2BFinance&sort=metastaffLastName"
    ]
    
    num_ranks = 12
    profile_urls = []

    for base_urls in departments_urls:
        start_rank = 1
        # Loop to paginate through the list of profiles
        while True:
            page_url = f"{base_urls}&startRank={start_rank}&numRanks={num_ranks}"
            urls = profile(page_url, driver)
            if not urls:
                break
            profile_urls.extend(urls)
            start_rank += num_ranks
            time.sleep(1)

    all_data = []
    for url in profile_urls:
        name, publications_info = scraping(url, driver)
        for pub in publications_info:
            all_data.append(pub + [name, url])

    # csv_filename = "UNSW.csv"
    # csv_header = ["Title", "Year", "Type", "Journal", "Article URL", "Researcher Name", "Profile URL"]
    # with open(csv_filename, mode="w", newline='', encoding="utf-8-sig") as f:
    #     writer = csv.writer(f)
    #     writer.writerow(csv_header)
    #     for url in profile_urls:
    #         name, publications_info = scraping(url, driver)
    #         for pub in publications_info:
    #             writer.writerow(pub + [name, url])
    
    driver.quit()
    # end_time = time.time()  # End timer
    # elapsed = end_time - start_time
    print("Scraping complete. Data saved to UNSW.csv")
    # print(f"Elapsed time: {elapsed:.2f} seconds")
    return all_data

# if __name__ == "__main__":
#     main()
