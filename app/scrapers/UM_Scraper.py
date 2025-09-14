from selenium import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from pyalex import Works, Authors, Institutions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import re
import csv

links_to_scrape = [("https://fbe.unimelb.edu.au/about/academic-staff?queries_tags_query=4895953", "Finance"),
                   ("https://fbe.unimelb.edu.au/about/academic-staff?queries_tags_query=4895951", "Accounting")]

#Only works for newer layout of researcher profile pages
def find_researcher(academic, driver):

    driver.get(academic["url"])

    try:
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        
    except TimeoutException:
        
        raise RuntimeError(f"Unable to load profile page for {academic['name']}")

    try:
        new_name = driver.find_element(By.XPATH, '//div[@id="profileTitleCol"]//h1')
    except NoSuchElementException:
        
        return(None)
        
    new_name = new_name.text

    

    if new_name == academic["name"]:
        return(None)
    else:
        academic["name"] = new_name
        return(new_name)

def transform_name_firstlast(name):
    # Remove anything inside parentheses including the parentheses themselves
    cleaned_name = re.sub(r"\s*\(.*?\)\s*", " ", name)
    # Collapse multiple spaces into one, and strip leading/trailing spaces
    return re.sub(r"\s+", " ", cleaned_name).strip()

#Uses nickname as first name
def transform_name_nicknamelast(name):
    # Look for "(nickname)" using regex
    match = re.search(r"\((.*?)\)", name)
    parts = name.split()
    
    if match:  
        # nickname inside parentheses
        nickname = match.group(1).strip()
        last_name = parts[-1]  # last word is the surname
        return(f"{nickname} {last_name}")
    else:
        return(name)

def get_staff(url, driver, field):
    driver.get(url)
    
    try:
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except TimeoutException:
        raise RuntimeError("Unable to load staff profile page")
    
    name_links = driver.find_elements(By.XPATH, "//div[@id='top']//div[@id='main-content']//div[@class='content-block__inner']/table//tr/td[1]/h5/a")
    roles = driver.find_elements(By.XPATH, "//div[@id='top']//div[@id='main-content']//div[@class='content-block__inner']/table//tr/td[1]/p")

    staff = []
    for staff_link, role in zip(name_links, roles):
        staff.append({
            "name": staff_link.text,
            "url": staff_link.get_attribute("href"),
            "role": role.text,
            "field": field,                 # <-- keep field with each academic
            "scraped": False,               # (moved here so every dict has it)
        })
    
    return(staff)

def clean_staff(staff_list):
    accepted_roles = ["Associate Professor", "Professor", "Senior Lecturer", "Lecturer", "Research Fellow"]
    rejected_roles = {"Assistant Lecturer", "Education-Focused", "Education Focused", "Education Focussed"}
    cleaned_staff_list = []
    
    for staff in staff_list:
        #checks name and role as it is inconsistent on the site
        if any(rejected_role in staff["role"] for rejected_role in rejected_roles):
            continue
        
        matched_role = next((role for role in accepted_roles if role in staff["role"] or role in staff["name"]),None)
        if matched_role is None:
            continue

        #removes role from their names
        for title in ["Associate Professor", "Professor", "Senior Lecturer", "Lecturer", "Research Fellow", "Dr ", "Mr ", "Ms "]:
            staff["name"] = staff["name"].replace(title, "")
        
        staff["name"] = staff["name"].strip()
        staff["role"] = staff["role"].replace("\n", " ")
        staff["role"] = matched_role
        staff["scraped"] = False
        
        cleaned_staff_list.append(staff)

    return(cleaned_staff_list)

def get_works_openalex(academics):
    
    UniMelb_works = []

    insts = Institutions().search("University of Melbourne").get()
    print(f"{len(insts)} search result(s) found for the institution")
    inst_id = insts[0]["id"].replace("https://openalex.org/", "")

    count = 0
    skipped_academics = []
    for academic in (a for a in academics if not a["scraped"]):
        auths = Authors().search(academic["name"]).filter(affiliations={"institution": {"id": inst_id}}).get()
        print(f"{len(auths)} search result(s) found for {academic['name']}")

        try:
            auth_id = auths[0]["id"].replace("https://openalex.org/", "")
        except IndexError:
            print("Skipping due to no results")
            skipped_academics.append(academic["name"])
            continue

        pager = Works().filter(author={"id": auth_id}).paginate(per_page=200)

        works = []
        for page in pager:
            for work in page:
                works.append(work)

        print(f"{len(works)} work(s) found for {academic['name']}")

        # store works in dict by name for deduplication
        auth_works = {}

        for work in works:
            work_id = work["id"].replace("https://openalex.org/", "")
            this_work = Works()[work_id]

            work_name = this_work["display_name"]
            try:
                work_source = this_work["primary_location"]["source"]["display_name"]
                work_date = this_work["publication_date"][:4]
                work_type = this_work["type"]
                work_link = this_work["doi"]
            except (TypeError, KeyError, ValueError):
                continue

            if work_name not in auth_works:
                # first time seeing this work name
 

                auth_works[work_name] = ( [ work_name, work_date, work_type, work_source, work_link, academic["name"], academic["url"], academic["role"] , academic["field"] ] )

            else:
                existing_source = auth_works[work_name][3]

                # replace if the existing one is from SSRN
                if existing_source == "SSRN Electronic Journal":
                    auth_works[work_name][3] = work_source
                    auth_works[work_name][1] = work_date

        # convert back to a list
        for work in auth_works:
            UniMelb_works.append(auth_works[work])
        
        academic["scraped"] = True
        count += 1

    print(f"Researchers scraped: {count}")
    print(f"Skipped due to no search results: {skipped_academics}")
    return UniMelb_works

def get_works_website(academics, driver):

    print("Attempting to scrape from UniMelb website")

    all_works = []
    First = True
    count = 0
    for academic in (a for a in academics if not a["scraped"]):
        time.sleep(5)
        #Some researchers' names are different on the department page and Find and Expert. This only looks up if needed to avoid unnecessary requests
        search_name = transform_name_firstlast(academic["name"])
        attempts = 0
        while attempts < 2:
            try:
                driver.get(f"https://findanexpert.unimelb.edu.au/searchresults?category=publication&pageNumber=1&pageSize=250&q={search_name}&sorting=mostRecent")
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'container-fluid') and .//a[contains(@href, '/scholarlywork/')]]")))
                break  # Successfully found publications, exit loop
            except TimeoutException:
                attempts += 1
                if attempts == 1:
                    print(f"Timeout waiting for publications to load for {academic['name']}. Trying nickname transformation")
                    # Try nickname transformation as fallback
                    search_name = transform_name_nicknamelast(academic["name"])
                    continue
                
                # If both transformations failed, try to find the researcher's actual name
                print(f"Both name transformations failed for {academic['name']}. Checking researcher profile")
                try:
                    new_name = find_researcher(academic, driver)
                    if new_name:
                        print(f"Found new name: {new_name}. Retrying with original transformation")
                        search_name = transform_name_firstlast(new_name)
                        attempts = 0  # Reset attempts to try again
                        continue
                except RuntimeError:
                    pass
                
                # If we get here, we've exhausted all options
                print(f"Could not find publications for {academic['name']}")
                break
        
        # If we didn't break out of the loop due to success, skip this academic
        if attempts >= 2:
            continue
        
        print(f"Scraping articles for {academic['name']}")

        try:
            pub_titles = driver.find_elements(By.XPATH, "//div[contains(@class, 'container-fluid') and .//a[contains(@href, '/scholarlywork/')]]//h4[contains(@class, 'font-weight-bold lead') and not(ancestor::div[contains(@class, 'new-feature-card')])]")
            pub_details_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'container-fluid') and .//a[contains(@href, '/scholarlywork/')]]//p[contains(@class, 'mb-1 w-100')]")
            pub_links = driver.find_elements(By.XPATH, "//div[contains(@class, 'container-fluid') and .//a[contains(@href, '/scholarlywork/')]]//a[contains(@href, '/scholarlywork/')]")
        except NoSuchElementException:
            print(f"Elements missing for {academic['name']}")
            continue
        
        #Join details from their sub-elements
        pub_details_text = []
        for element in pub_details_elements:
            pub_details_text.append(element.text)

        #Sanitise the details and turn them into a list
        for i in range(len(pub_details_text)):
            details = pub_details_text[i].split("|")
            
            for j in range(len(details)):
                details[j] = details[j].strip()
            
            while len(details) < 3:
                details.append(None)

            #details format: [type, year, source]
            pub_details_text[i] = details

        for i in range(0, len(pub_titles)):


            all_works.append([
                pub_titles[i].text,
                pub_details_text[i][1],
                pub_details_text[i][0],
                pub_details_text[i][2],
                pub_links[i].get_attribute('href'),
                academic["name"],
                academic["url"],
                academic["role"],
                academic["field"] 
            ])

            academic["scraped"] = True
        
        count += 1
    
    print(f"Researchers scraped: {count}")
    return(all_works)


def scrape_UM():
    csv_header = ["Title", "Year", "Type", "Journal Name", "Article URL", "Researcher Name", "Profile URL", "Job Title", "Field", "Level"]
    with open("app/files/ANU_data.csv", mode="w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)

    driver = uc.Chrome() #removed version_main=138
    for url, field in links_to_scrape:
        staff_list = get_staff(url, driver, field)

        academic_list = clean_staff(staff_list)
        with open("app/files/UM_data.csv", mode="a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(get_works_website(academic_list, driver))
            writer.writerows(get_works_openalex(academic_list))
