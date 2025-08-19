from selenium import webdriver
from selenium.webdriver.common.by import By
from pyalex import Works, Authors, Institutions

def get_staff(url):
    driver = webdriver.Chrome()
    driver.get(url)
    
    driver.implicitly_wait(5)
    
    name_links = driver.find_elements(By.XPATH, "//div[@id='top']//div[@id='main-content']//div[@class='content-block__inner']/table//tr/td[1]/h5/a")
    roles = driver.find_elements(By.XPATH, "//div[@id='top']//div[@id='main-content']//div[@class='content-block__inner']/table//tr/td[1]/p")
    
    staff = []
    for staff_link, role in zip(name_links, roles):
        staff.append({"name": staff_link.text, "url": staff_link.get_attribute("href"), "role": role.text})
    
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
        for title in ["Associate Professor", "Professor", "Senior Lecturer", "Lecturer", "Research Fellow", "Dr"]:
            staff["name"] = staff["name"].replace(title, "")
        
        staff["name"] = staff["name"].strip()
        staff["role"] = staff["role"].replace("\n", " ")
        staff["role"] = staff["role"].strip()
        
        cleaned_staff_list.append(staff)

    return(cleaned_staff_list)

def get_works_openalex(academics):
    UniMelb_works = {}

    insts = Institutions().search("University of Melbourne").get()
    print(f"{len(insts)} search result(s) found for the institution")
    inst_id = insts[0]["id"].replace("https://openalex.org/", "")

    skipped_academics = []
    for academic in academics:
        auths = Authors().search(academic["name"]).filter(affiliations={"institution":{"id":inst_id}}).get()
        print(f"{len(auths)} search result(s) found for {academic['name']}")
        
        try:
            auth_id = auths[0]["id"].replace("https://openalex.org/", "")
        except IndexError:
            print("Skipping due to no results")
            skipped_academics.append(academic["name"])
            continue

        works = Works().filter(author={"id":auth_id}).get()
        print(f"{len(works)} work(s) found for {academic['name']}")

        auth_works = set()
        skip_count = 0
        for work in works:
            work_id = work["id"].replace("https://openalex.org/", "")
            
            this_work = Works()[work_id]

            work_name = this_work["display_name"]
            try:
                work_source = this_work["primary_location"]["source"]["display_name"]
                work_date = this_work["publication_date"]
            except TypeError:
                skip_count += 1
                continue
            
            auth_works.add((work_name, work_source, work_date))
        
        UniMelb_works[academic["name"]] = auth_works

    print(f'Skipped due to no search results: {skipped_academics}')

    return(UniMelb_works)

def main():
    staff_list = get_staff("https://fbe.unimelb.edu.au/about/academic-staff?queries_tags_query=4895953")
    academic_list = clean_staff(staff_list)
    UniMelb_works = get_works_openalex(academic_list)
    
    return(UniMelb_works)

dic = main()
print(dic)