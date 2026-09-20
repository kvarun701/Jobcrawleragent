import asyncio
import json
import re
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def extract_experience(title, text=""):
    combined = f"{title} {text}".lower()
    # Match patterns like "X-Y yrs", "X to Y years"
    m = re.search(r'(\d+)\s*(?:-|to)\s*(\d+)\s*(?:yrs|years|yr)', combined)
    if m:
        return f"{m.group(1)}-{m.group(2)} Yrs"
    # Match patterns like "X+ yrs"
    m_plus = re.search(r'(\d+)\+\s*(?:yrs|years|yr)', combined)
    if m_plus:
        return f"{m_plus.group(1)}+ Yrs"
    if any(w in combined for w in ["fresher", "intern", "internship", "trainee", "entry level", "graduate"]):
        return "0-1 Yrs (Fresher)"
    if any(w in combined for w in ["junior", "jr", "associate", "sde 1", "sde-1", "sde1", "l1", "l2"]):
        return "1-3 Yrs"
    if any(w in combined for w in ["mid", "sde 2", "sde-2", "sde2", "l3"]):
        return "3-5 Yrs"
    if any(w in combined for w in ["senior", "sr", "sde 3", "sde-3", "sde3", "lead", "specialist"]):
        return "5-8 Yrs"
    if any(w in combined for w in ["principal", "staff", "architect", "manager", "director", "head", "vp"]):
        return "8+ Yrs"
    return "Not specified"

def get_linkedin_exp_param(exp):
    if exp is None:
        return ""
    if exp == 0:
        return "1,2"      # Internship, Entry level
    elif exp <= 2:
        return "2"        # Entry level
    elif exp <= 4:
        return "3"        # Associate
    elif exp <= 8:
        return "4"        # Mid-Senior level
    elif exp <= 12:
        return "4,5"      # Mid-Senior, Director
    else:
        return "5,6"      # Director, Executive

async def scrape_linkedin(context, keyword, location, experience=None):
    jobs = []
    kw_clean = keyword.strip()
    loc_clean = location.strip()
    exp_log = f", Exp: {experience} Yrs" if experience is not None else ""
    print(f"Scraping LinkedIn for '{kw_clean}' in '{loc_clean}' (Last 24 hours{exp_log})...")
    page = None
    try:
        page = await context.new_page()
        # f_TPR=r86400 restricts to past 24 hours, sortBy=DD orders by most recent
        f_e = get_linkedin_exp_param(experience)
        f_e_param = f"&f_E={f_e}" if f_e else ""
        url = f"https://www.linkedin.com/jobs/search/?keywords={urllib.parse.quote(kw_clean)}&location={urllib.parse.quote(loc_clean)}&f_TPR=r86400&sortBy=DD{f_e_param}"
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        
        try:
            await page.wait_for_selector('ul.jobs-search__results-list li', timeout=8000)
        except Exception:
            pass

        job_cards = await page.query_selector_all('ul.jobs-search__results-list li')
        for card in job_cards[:10]:
            try:
                title_elem = await card.query_selector('h3.base-search-card__title')
                title = await title_elem.inner_text() if title_elem else "N/A"
                
                company_elem = await card.query_selector('h4.base-search-card__subtitle a')
                if not company_elem:
                    company_elem = await card.query_selector('h4.base-search-card__subtitle')
                company = await company_elem.inner_text() if company_elem else "N/A"
                
                location_elem = await card.query_selector('span.job-search-card__location')
                loc = await location_elem.inner_text() if location_elem else "N/A"
                
                date_elem = await card.query_selector('time.job-search-card__listdate, time.job-search-card__listdate--new, time')
                posted = (await date_elem.inner_text()).strip() if date_elem else "Past 24 hours"
                
                link_elem = await card.query_selector('a.base-card__full-link')
                link = await link_elem.get_attribute('href') if link_elem else "N/A"
                if link != "N/A":
                    link = link.split('?')[0]  # Clean tracking parameters
                
                exp_text = extract_experience(title)
                if exp_text == "Not specified" and experience is not None:
                    exp_text = f"{experience} Yrs" if experience > 0 else "0-1 Yrs (Fresher)"

                if title.strip() and title != "N/A":
                    jobs.append({
                        "Platform": "LinkedIn",
                        "Title": title.strip(),
                        "Company": company.strip(),
                        "Location": loc.strip(),
                        "Experience": exp_text,
                        "Posted": posted,
                        "Link": link
                    })
            except Exception:
                continue
    except Exception as e:
        print(f"LinkedIn scraping notice: {e}")
    finally:
        if page:
            await page.close()
            
    print(f"LinkedIn returned {len(jobs)} jobs.")
    return jobs

INDIAN_LOCATIONS = {
    "india", "noida", "delhi", "new delhi", "bengaluru", "bangalore", "hyderabad",
    "pune", "mumbai", "chennai", "gurgaon", "gurugram", "kolkata", "ahmedabad",
    "jaipur", "chandigarh", "lucknow", "indore", "bhopal", "kerala", "karnataka",
    "tamil nadu", "maharashtra", "uttar pradesh", "gujarat", "haryana", "rajasthan",
    "punjab", "telangana", "andhra pradesh", "kochi", "coimbatore", "mysore", "nagpur",
    "vadodara", "surat", "patna", "bhubaneswar", "thiruvananthapuram", "ncr", "delhi ncr"
}

def is_indian_region(location, region="auto"):
    if region and "india" in region.lower():
        return True
    if region and any(k in region.lower() for k in ["us", "global", "united states"]):
        return False
    loc = location.strip().lower()
    if not loc:
        return True
    return any(k in loc for k in INDIAN_LOCATIONS)

async def scrape_indeed(context, keyword, location, region="auto", experience=None):
    jobs = []
    is_in = is_indian_region(location, region)
    domain = "in.indeed.com" if is_in else "www.indeed.com"
    
    kw_raw = keyword.strip()
    if experience is not None:
        if experience == 0:
            kw_search = f"{kw_raw} fresher"
        elif experience >= 10:
            kw_search = f"{kw_raw} lead"
        elif experience >= 5:
            kw_search = f"{kw_raw} senior"
        else:
            kw_search = f"{kw_raw} {experience} years"
    else:
        kw_search = kw_raw
        
    kw_enc = urllib.parse.quote_plus(kw_search)
    loc_clean = location.strip().lower()
    if is_in and loc_clean in ["india", "in", "all", ""]:
        url = f"https://{domain}/jobs?q={kw_enc}&fromage=1&sort=date"
    else:
        url = f"https://{domain}/jobs?q={kw_enc}&l={urllib.parse.quote_plus(location.strip())}&fromage=1&sort=date"
        
    exp_log = f", Exp: {experience} Yrs" if experience is not None else ""
    print(f"Scraping Indeed ({domain}) for '{kw_raw}' in '{location.strip()}' (Last 24 hours{exp_log})...")
    page = None
    try:
        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)
        
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        
        # Wait for dynamic rendering
        await page.wait_for_timeout(2000)
            
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        title_links = soup.select("a.jcs-JobTitle")
        if not title_links:
            title_links = soup.select("h2.jobTitle a, [data-testid='job-title']")
            
        for a in title_links[:10]:
            try:
                title = a.get_text(strip=True)
                if not title or title == "N/A":
                    continue
                    
                href = a.get("href", "")
                if not href or href in ["#", "javascript:void(0)", ""]:
                    continue
                link = f"https://{domain}{href}" if href.startswith("/") else href
                
                card = a.find_parent("div", class_=lambda c: c and any(k in c for k in ["cardOutline", "job_seen_beacon", "resultContent"]))
                if not card:
                    card = a.find_parent("li") or a.find_parent("div")
                    
                comp_elem = card.select_one("[data-testid='company-name'], span.companyName, [class*='companyName']") if card else None
                company = comp_elem.get_text(strip=True) if comp_elem else "N/A"
                
                loc_elem = card.select_one("[data-testid='text-location'], div.companyLocation, [class*='companyLocation']") if card else None
                loc = loc_elem.get_text(strip=True) if loc_elem else "N/A"
                
                date_elem = card.select_one("[data-testid='myJobsStateDate'], span.date, .date, [class*='date']") if card else None
                posted = date_elem.get_text(strip=True).replace("EmployerActive", "").replace("Posted", "").strip() if date_elem else "Past 24 hours"
                if not posted:
                    posted = "Past 24 hours"
                
                card_text = card.get_text(" ", strip=True) if card else ""
                exp_text = extract_experience(title, card_text)
                if exp_text == "Not specified" and experience is not None:
                    exp_text = f"{experience} Yrs" if experience > 0 else "0-1 Yrs (Fresher)"

                if company == "N/A" and loc == "N/A":
                    continue
                
                jobs.append({
                    "Platform": "Indeed",
                    "Title": title,
                    "Company": company,
                    "Location": loc,
                    "Experience": exp_text,
                    "Posted": posted,
                    "Link": link
                })
            except Exception:
                continue
    except Exception as e:
        print(f"Indeed scraping notice: {e}")
    finally:
        if page:
            await page.close()
            
    print(f"Indeed returned {len(jobs)} jobs.")
    return jobs

def clean_naukri_location(location):
    if not location:
        return ""
    loc_clean = location.strip()
    # Normalize punctuation and split into words
    parts = [p.strip() for p in loc_clean.replace(",", " ").split() if p.strip()]
    # If location combines country and city like "India noida" or "Noida, India", extract the city
    non_country = [p for p in parts if p.lower() not in ["india", "in", "pan-india", "pan"]]
    if non_country:
        return " ".join(non_country)
    return ""  # If only "India", leave blank for pan-India search

async def scrape_naukri(context, keyword, location, experience=None):
    jobs = []
    kw_clean = keyword.strip()
    target_loc = clean_naukri_location(location)
    exp_log = f", Exp: {experience} Yrs" if experience is not None else ""
    print(f"Scraping Naukri for '{kw_clean}' in '{target_loc or 'India'}' (Last 24 hours{exp_log})...")
    page = None
    try:
        page = await context.new_page()
        
        # Intercept and modify search API request to inject experience and jobAge
        async def modify_search_request(route, request):
            url = request.url
            if "jobapi/v3/search" in url:
                params = []
                if "experience=" not in url and experience is not None:
                    params.append(f"experience={experience}")
                if "jobAge=" not in url:
                    params.append("jobAge=1")
                if params:
                    sep = "&" if "?" in url else "?"
                    new_url = f"{url}{sep}{'&'.join(params)}"
                    await route.continue_(url=new_url)
                    return
            await route.continue_()

        await page.route("**/jobapi/v3/search*", modify_search_request)

        # Format Naukri search URL
        if target_loc:
            url = f"https://www.naukri.com/jobs-in-india?k={urllib.parse.quote(kw_clean)}&l={urllib.parse.quote(target_loc)}"
        else:
            url = f"https://www.naukri.com/jobs-in-india?k={urllib.parse.quote(kw_clean)}"

        captured_datasets = []
        async def handle_response(response):
            if "jobapi/v3/search" in response.url:
                try:
                    data = await response.json()
                    captured_datasets.append((response.url, data))
                except Exception:
                    pass

        page.on("response", handle_response)
        
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        
        # Wait initial load
        await page.wait_for_timeout(2500)
        
        # If jobAge wasn't triggered yet, select Freshness -> Last 1 day filter
        if not any("jobAge=1" in u for u, _ in captured_datasets):
            try:
                trigger = page.locator("[data-filter-id='freshness']").first
                if await trigger.count() > 0:
                    await trigger.click()
                    await page.wait_for_timeout(400)
                    opt = page.locator("li").filter(has_text="Last 1 day").first
                    if await opt.count() > 0 and await opt.is_visible():
                        await opt.click()
                        await page.wait_for_timeout(1500)
            except Exception as e:
                print(f"Naukri freshness filter notice: {e}")
            
        # Prioritize response matching our filters
        chosen_data = None
        for u, d in reversed(captured_datasets):
            if "jobAge=1" in u and (experience is None or f"experience={experience}" in u):
                chosen_data = d
                break
        if not chosen_data:
            for u, d in reversed(captured_datasets):
                if "jobAge=1" in u:
                    chosen_data = d
                    break
        if not chosen_data and captured_datasets:
            chosen_data = captured_datasets[-1][1]
            
        if chosen_data:
            raw_jobs = chosen_data.get("jobDetails", [])
            for j in raw_jobs[:10]:
                title = j.get("title", "N/A").strip()
                company = j.get("companyName", "N/A").strip()
                loc = next((p["label"] for p in j.get("placeholders", []) if p.get("type") == "location"), location).strip()
                job_id = j.get("jobId", "")
                link = ("https://www.naukri.com" + j.get("jdURL")) if j.get("jdURL") else f"https://www.naukri.com/job-listings-{job_id}"
                posted = j.get("footerPlaceholderLabel") or ("Today" if j.get("todaysJob") else "Past 24 hours")
                
                exp_text = j.get("experienceText")
                if not exp_text and j.get("minimumExperience") is not None:
                    exp_text = f"{j.get('minimumExperience')}-{j.get('maximumExperience')} Yrs"
                if not exp_text and experience is not None:
                    exp_text = f"{experience} Yrs" if experience > 0 else "0-1 Yrs (Fresher)"
                if not exp_text:
                    exp_text = extract_experience(title)

                if title and title != "N/A":
                    jobs.append({
                        "Platform": "Naukri",
                        "Title": title,
                        "Company": company,
                        "Location": loc,
                        "Experience": exp_text,
                        "Posted": posted,
                        "Link": link
                    })
                    
        # Fallback to DOM parsing if API didn't populate jobs
        if not jobs:
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            tuples = soup.select(".srp-jobtuple-wrapper, .cust-job-tuple, [data-job-id]")
            for card in tuples[:10]:
                title_elem = card.select_one("a.title")
                comp_elem = card.select_one("a.comp-name, .comp-name")
                loc_elem = card.select_one(".loc-wrap, .locWdth, .location, span.loc")
                date_elem = card.select_one(".job-post-day, .ni-job-tuple-icon-day, [class*='day'], [class*='post']")
                exp_elem = card.select_one(".exp-wrap, .expwdth, .experience, [class*='exp']")
                
                title = title_elem.get_text(strip=True) if title_elem else "N/A"
                company = comp_elem.get_text(strip=True) if comp_elem else "N/A"
                loc = loc_elem.get_text(strip=True) if loc_elem else (target_loc or location)
                posted = date_elem.get_text(strip=True) if date_elem else "Past 24 hours"
                exp_text = exp_elem.get_text(strip=True) if exp_elem else extract_experience(title)
                if exp_text == "Not specified" and experience is not None:
                    exp_text = f"{experience} Yrs" if experience > 0 else "0-1 Yrs (Fresher)"
                link = title_elem.get("href", "N/A") if title_elem else "N/A"
                
                if title and title != "N/A":
                    jobs.append({
                        "Platform": "Naukri",
                        "Title": title,
                        "Company": company,
                        "Location": loc,
                        "Experience": exp_text,
                        "Posted": posted,
                        "Link": link
                    })

    except Exception as e:
        print(f"Naukri scraping notice: {e}")
    finally:
        if page:
            await page.close()
            
    print(f"Naukri returned {len(jobs)} jobs.")
    return jobs

async def scrape_remoteok(keyword, location="Remote", experience=None):
    jobs = []
    exp_log = f", Exp: {experience} Yrs" if experience is not None else ""
    print(f"Scraping Remote OK for '{keyword}' (Last 24 hours{exp_log})...")
    try:
        def fetch_api(url):
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        
        loop = asyncio.get_event_loop()
        import datetime
        now_epoch = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        words = [w.lower() for w in keyword.split() if len(w) > 2]
        
        # Build endpoints to query: specific tag endpoints first, then fallback general endpoint
        urls = [f"https://remoteok.com/api?tag={urllib.parse.quote(w)}" for w in words[:3]]
        urls.append("https://remoteok.com/api")
        
        seen_ids = set()
        
        for url in urls:
            try:
                data = await loop.run_in_executor(None, fetch_api, url)
                if not isinstance(data, list):
                    continue
                    
                for item in data:
                    if not isinstance(item, dict) or not item.get("position"):
                        continue
                    item_id = item.get("id") or item.get("url")
                    if item_id in seen_ids:
                        continue
                        
                    pos = item.get("position", "")
                    comp = item.get("company", "")
                    tags = " ".join(item.get("tags", [])) if isinstance(item.get("tags"), list) else ""
                    searchable_text = f"{pos} {comp} {tags}".lower()
                    
                    matches = [w in searchable_text for w in words] if words else [True]
                    if any(matches):
                        seen_ids.add(item_id)
                        
                        epoch = int(item.get("epoch") or 0)
                        diff_hours = (now_epoch - epoch) / 3600 if epoch > 0 else 999
                        if diff_hours <= 24:
                            posted = f"{int(diff_hours)}h ago" if diff_hours >= 1 else "Just now"
                            recency_bonus = 10
                        elif diff_hours <= 48:
                            posted = "1d ago"
                            recency_bonus = 5
                        else:
                            days = int(diff_hours / 24)
                            posted = f"{days}d ago"
                            recency_bonus = 0

                        exp_bonus = 0
                        exp_text = extract_experience(pos, tags)
                        if experience is not None:
                            if experience == 0 and any(w in searchable_text for w in ["junior", "entry", "intern"]):
                                exp_bonus = 5
                            elif experience >= 5 and any(w in searchable_text for w in ["senior", "lead", "staff", "principal"]):
                                exp_bonus = 5
                            if exp_text == "Not specified":
                                exp_text = f"{experience} Yrs" if experience > 0 else "0-1 Yrs (Fresher)"

                        jobs.append({
                            "Platform": "Remote OK",
                            "Title": pos.strip(),
                            "Company": comp.strip(),
                            "Location": (item.get("location") or "Remote").strip(),
                            "Experience": exp_text,
                            "Posted": posted,
                            "Link": item.get("url", "N/A"),
                            "_score": sum(matches) * 2 + recency_bonus + exp_bonus
                        })
                        if len(jobs) >= 20:
                            break
            except Exception:
                continue
                
            if len(jobs) >= 10:
                break
                
        # Sort by relevance, recency, and experience match
        jobs.sort(key=lambda x: x.get("_score", 0), reverse=True)
        jobs = jobs[:10]
        for j in jobs:
            j.pop("_score", None)
            
    except Exception as e:
        print(f"Remote OK scraping notice: {e}")
        
    print(f"Remote OK returned {len(jobs)} jobs.")
    return jobs

async def scrape_ziprecruiter(context, keyword, location, experience=None):
    jobs = []
    print(f"Scraping ZipRecruiter for '{keyword}' in '{location}'...")
    page = None
    try:
        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)
        params = urllib.parse.urlencode({"search": keyword, "location": location})
        url = f"https://www.ziprecruiter.com/jobs-search?{params}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)

        try:
            await page.wait_for_selector('article.job_result, div.job_result', timeout=5000)
        except Exception:
            return jobs

        job_cards = await page.query_selector_all('article.job_result, div.job_result')
        for card in job_cards[:10]:
            try:
                title_elem = await card.query_selector('h2.job_title, h2 a, [data-testid="job-title"]')
                company_elem = await card.query_selector('.company_name, [data-testid="company-name"]')
                location_elem = await card.query_selector('.location, [data-testid="job-location"]')
                link_elem = await card.query_selector('h2 a, a.job_link, a[data-testid="job-title"]')

                title = await title_elem.inner_text() if title_elem else "N/A"
                company = await company_elem.inner_text() if company_elem else "N/A"
                loc = await location_elem.inner_text() if location_elem else "N/A"
                link = await link_elem.get_attribute('href') if link_elem else None
                if link and link.startswith('/'):
                    link = f"https://www.ziprecruiter.com{link}"

                exp_text = extract_experience(title)
                if exp_text == "Not specified" and experience is not None:
                    exp_text = f"{experience} Yrs" if experience > 0 else "0-1 Yrs (Fresher)"

                if title.strip() and title != "N/A":
                    jobs.append({
                        "Platform": "ZipRecruiter",
                        "Title": title.strip(),
                        "Company": company.strip(),
                        "Location": loc.strip(),
                        "Experience": exp_text,
                        "Posted": "Past 24 hours",
                        "Link": link or "N/A"
                    })
            except Exception:
                continue
    except Exception as e:
        print(f"ZipRecruiter scraping notice: {e}")
    finally:
        if page:
            await page.close()
            
    print(f"ZipRecruiter returned {len(jobs)} jobs.")
    return jobs

async def run_scraper(keyword, location, region="auto", experience=None):
    exp_log = f", Experience: {experience} Yrs" if experience is not None else ""
    print(f"Starting multi-platform scraper for '{keyword}' in '{location}' (Region: {region}{exp_log})...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        is_in = is_indian_region(location, region)
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1440, "height": 900},
            locale="en-IN" if is_in else "en-US",
            extra_http_headers={
                "Accept-Language": "en-IN,en-US,en;q=0.9" if is_in else "en-US,en;q=0.9",
                "Sec-Ch-Ua": "\"Google Chrome\";v=\"124\", \"Chromium\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": "\"macOS\""
            }
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)
        
        # Run scrapers concurrently for high performance
        tasks = [
            scrape_linkedin(context, keyword, location, experience=experience),
            scrape_indeed(context, keyword, location, region=region, experience=experience),
            scrape_naukri(context, keyword, location, experience=experience),
            scrape_remoteok(keyword, location, experience=experience)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        await browser.close()
        
        all_jobs = []
        for res in results:
            if isinstance(res, list):
                all_jobs.extend(res)
            elif isinstance(res, Exception):
                print(f"Scraper error: {res}")
                
        print(f"Total jobs collected across all platforms: {len(all_jobs)}")
        return all_jobs
