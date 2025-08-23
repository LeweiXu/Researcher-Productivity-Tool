from selenium import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from pyalex import Works, Authors, Institutions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time
import random

links_to_scrape = ["https://fbe.unimelb.edu.au/about/academic-staff?queries_tags_query=4895953", "https://fbe.unimelb.edu.au/about/academic-staff?queries_tags_query=4895951"]

def get_staff(url):
    driver = webdriver.Chrome()
    driver.get(url)
    
    WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    
    name_links = driver.find_elements(By.XPATH, "//div[@id='top']//div[@id='main-content']//div[@class='content-block__inner']/table//tr/td[1]/h5/a")
    roles = driver.find_elements(By.XPATH, "//div[@id='top']//div[@id='main-content']//div[@class='content-block__inner']/table//tr/td[1]/p")

    staff = []
    for staff_link, role in zip(name_links, roles):
        staff.append({"name": staff_link.text, "url": staff_link.get_attribute("href"), "role": role.text})
    
    driver.close()
    return(staff)

def clean_staff(staff_list):
    accepted_roles = {"Professor", "Associate Professor", "Lecturer", "Senior Lecturer", "Research Fellow"}
    rejected_roles = {"Assistant Lecturer", "Education-Focused", "Education Focused", "Education Focussed"}
    cleaned_staff_list = []
    
    for staff in staff_list:
        #checks name and role as it is inconsistent on the site
        if not any(accepted_role in staff["role"] for accepted_role in accepted_roles) and not any(accepted_role in staff["name"] for accepted_role in accepted_roles):
            continue
        
        if any(rejected_role in staff["role"] for rejected_role in rejected_roles):
            continue
        
        #removes role from their names
        for title in ["Associate Professor", "Professor", "Senior Lecturer", "Lecturer", "Research Fellow", "Dr", "Mr", "Ms"]:
            staff["name"] = staff["name"].replace(title, "")
        
        staff["name"] = staff["name"].strip()
        staff["role"] = staff["role"].replace("\n", " ")
        staff["role"] = staff["role"].strip()
        staff["scraped"] = False
        
        cleaned_staff_list.append(staff)

    return(cleaned_staff_list)

def get_works_openalex(academics):
    UniMelb_works = []

    insts = Institutions().search("University of Melbourne").get()
    print(f"{len(insts)} search result(s) found for the institution")
    inst_id = insts[0]["id"].replace("https://openalex.org/", "")

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
                auth_works[work_name] = ([work_name, work_date, work_type, work_source, work_link, academic["name"], academic["url"]])
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

    print(f"Skipped due to no search results: {skipped_academics}")
    return UniMelb_works


#Cannot be run due to protections by the UniMelb site ()
def get_works_website(academics):
    
    options = uc.ChromeOptions()
    #options.add_argument(r"user-data-dir=C:\Users\jarra\temp\User Data")
    #options.add_argument(r'--profile-directory=Default')
    #options.add_argument("--headless=new")
    # options.add_argument("--log-level=3")
    # options.add_argument("--no-sandbox")
    # options.add_argument("--disable-gpu")
    # options.add_argument("--window-size=1280,800")
    # options.add_argument("--lang=en-US,en")
    # options.add_argument("--headless")  # Uncomment for headless mode
    driver = uc.Chrome(version_main=138, options=options)

    for academic in (a for a in academics if not a["scraped"]):
        time.sleep(random.uniform(5, 10))

        driver.get(academic["url"])
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        try:
            pub_desc = driver.find_element(By.XPATH, "//section[@id='publications']//p[@class='source-sans blue']")
        except NoSuchElementException:
            print(f"No publications for {academic['name']} found")
            continue
        
        print(pub_desc.text)
    
    driver.close()

def scrape_page(url):
    staff_list = get_staff(url)
    academic_list = clean_staff(staff_list)
    UniMelb_works = get_works_website(academic_list)
    #get_works_website(academic_list)

    return(UniMelb_works)

def scrape_UM():
    output = []
    for link in links_to_scrape:
        output.extend(scrape_page(link))
    
    return(output)