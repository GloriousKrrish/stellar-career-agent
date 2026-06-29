"""
Resilient Job Provider System.

Provider priority:
  1. Firecrawl API (scrapes Naukri + LinkedIn properly)
  2. RemoteOK API (free, no key required)
  3. Arbeitnow (free European API, works globally for remote)
  4. Internshala (India-focused, scrapable)
  5. Demo dataset fallback (always succeeds)

Never returns empty. Every provider failure falls through to next.
"""
from __future__ import annotations
import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable
import httpx
from logger import get_logger

log = get_logger("JobProviders")

async def _notify(on_progress: Callable[[str], Any] | None, msg: str):
    if not on_progress:
        return
    try:
        if asyncio.iscoroutinefunction(on_progress):
            await on_progress(msg)
        else:
            on_progress(msg)
    except Exception:
        pass

# ──────────────────────────────────────────────────────────────────────────────
# Data class (plain dict for simplicity, no Pydantic dep here)
# ──────────────────────────────────────────────────────────────────────────────

def make_job(
    title: str,
    company: str,
    location: str,
    salary: str,
    url: str,
    source: str,
    description: str = "",
    skills: list[str] | None = None,
    posted_at: str = "Recently",
) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "company": company,
        "location": location,
        "salary": salary,
        "url": url,
        "source": source,
        "description": description,
        "skills": skills or [],
        "posted_at": posted_at,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Provider 1: Firecrawl (uses our existing API key)
# ──────────────────────────────────────────────────────────────────────────────

async def fetch_firecrawl(role: str, location: str, firecrawl_key: str, on_progress: Callable[[str], Any] | None = None) -> list[dict]:
    """Use Firecrawl's scrape API to extract Naukri job listings cleanly."""
    jobs: list[dict] = []
    if not firecrawl_key:
        log.warning("Firecrawl key missing")
        return jobs

    await _notify(on_progress, "Firecrawl Scraper: Crawling Naukri using Firecrawl API...")

    encoded_role = role.replace(" ", "-").lower()
    encoded_loc = location.replace(" ", "-").lower() if location else ""
    if encoded_loc:
        naukri_url = f"https://www.naukri.com/{encoded_role}-jobs-in-{encoded_loc}"
    else:
        naukri_url = f"https://www.naukri.com/{encoded_role}-jobs"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {firecrawl_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": naukri_url,
                    "formats": ["markdown", "extract"],
                    "extract": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "jobs": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "title": {"type": "string"},
                                            "company": {"type": "string"},
                                            "location": {"type": "string"},
                                            "salary": {"type": "string"},
                                            "url": {"type": "string"},
                                            "experience": {"type": "string"},
                                            "skills": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
            )
            log.info(f"Firecrawl response: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                extracted = data.get("data", {}).get("extract", {}) or {}
                raw_jobs = extracted.get("jobs", []) or []
                log.info(f"Firecrawl extracted {len(raw_jobs)} jobs")
                await _notify(on_progress, f"Firecrawl Scraper: Extracted {len(raw_jobs)} Naukri jobs.")
                for j in raw_jobs[:20]:
                    if not j.get("title"):
                        continue
                    job_url = j.get("url", "")
                    if not job_url or "naukri.com" not in job_url.lower():
                        job_url = naukri_url

                    jobs.append(make_job(
                        title=j.get("title", ""),
                        company=j.get("company", "Unknown"),
                        location=j.get("location", location or "India"),
                        salary=j.get("salary", ""),
                        url=job_url,
                        source="NAUKRI",
                        skills=j.get("skills", []),
                    ))
            else:
                log.warning(f"Firecrawl error: {resp.status_code} — {resp.text[:200]}")
                await _notify(on_progress, f"Firecrawl Scraper: Failed (HTTP {resp.status_code}).")
    except Exception as e:
        log.error(f"Firecrawl fetch failed: {e}")
        await _notify(on_progress, "Firecrawl Scraper: Request failed.")
    return jobs


# ──────────────────────────────────────────────────────────────────────────────
# Provider 2: RemoteOK (free, no key, JSON API)
# ──────────────────────────────────────────────────────────────────────────────

async def fetch_remoteok(role: str, on_progress: Callable[[str], Any] | None = None) -> list[dict]:
    """RemoteOK free API — returns remote jobs worldwide."""
    jobs: list[dict] = []
    await _notify(on_progress, "RemoteOK Scraper: Fetching remote jobs via RemoteOK API...")
    role_lower = role.lower()
    # Try multiple tags derived from the role
    tag_map = {
        "full": ["fullstack", "javascript", "typescript"],
        "front": ["frontend", "react", "javascript"],
        "back": ["backend", "python", "node"],
        "data": ["data", "python", "sql"],
        "machine": ["machine-learning", "python", "ai"],
        "devops": ["devops", "aws", "cloud"],
        "product": ["product", "management"],
        "mobile": ["mobile", "react-native", "ios"],
        "react": ["react", "javascript", "frontend"],
        "node": ["node", "javascript", "backend"],
        "python": ["python", "backend"],
        "java": ["java", "backend"],
        "aws": ["aws", "devops", "cloud"],
        "ai": ["ai", "machine-learning", "python"],
    }
    first_word = role_lower.split()[0]
    tags_to_try = tag_map.get(first_word, [first_word, "dev"])

    try:
        async with httpx.AsyncClient(
            timeout=20,
            headers={
                "User-Agent": "StellarCareerAgent/2.0 (job search aggregator; contact@stellar.ai)",
                "Accept": "application/json",
            },
            follow_redirects=True,
        ) as client:
            for api_tag in tags_to_try:
                if jobs:
                    break
                url = f"https://remoteok.com/api?tag={api_tag}"
                resp = await client.get(url)
                log.info(f"RemoteOK status: {resp.status_code} for tag={api_tag}")
                if resp.status_code != 200:
                    continue
                data = resp.json()
                # First element is a legal notice dict, skip it
                raw_jobs = [x for x in data if isinstance(x, dict) and x.get("position")]
                log.info(f"RemoteOK found {len(raw_jobs)} jobs for tag={api_tag}")
                await _notify(on_progress, f"RemoteOK Scraper: Found {len(raw_jobs)} jobs for tag '{api_tag}'.")
                for j in raw_jobs[:20]:
                    salary_min = j.get("salary_min") or 0
                    salary_max = j.get("salary_max") or 0
                    salary = ""
                    if salary_min and salary_max:
                        salary = f"${salary_min:,}–${salary_max:,}/yr"
                    elif salary_min:
                        salary = f"${salary_min:,}+/yr"

                    tags_list = j.get("tags") or []
                    date_str = j.get("date", "")[:10] if j.get("date") else "Recently"

                    jobs.append(make_job(
                        title=j.get("position", ""),
                        company=j.get("company", "Unknown"),
                        location="Remote",
                        salary=salary,
                        url=j.get("url") or f"https://remoteok.com/jobs/{j.get('id', '')}",
                        source="REMOTEOK",
                        skills=tags_list[:6],
                        posted_at=date_str,
                    ))
                await asyncio.sleep(0.5)  # be polite
    except Exception as e:
        log.error(f"RemoteOK fetch failed: {e}")
    return jobs


# ──────────────────────────────────────────────────────────────────────────────
# Provider 3: Arbeitnow (free, no key, works for remote globally)
# ──────────────────────────────────────────────────────────────────────────────

async def fetch_arbeitnow(role: str, location: str, on_progress: Callable[[str], Any] | None = None) -> list[dict]:
    """Arbeitnow free job board API — remote-focused, no key needed."""
    jobs: list[dict] = []
    await _notify(on_progress, "Arbeitnow Scraper: Fetching remote jobs via Arbeitnow API...")
    try:
        # Build search query
        search = role.replace(" ", "+")
        url = f"https://www.arbeitnow.com/api/job-board-api?search={search}&page=1"

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url)
            log.info(f"Arbeitnow status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                raw_jobs = data.get("data", [])
                log.info(f"Arbeitnow found {len(raw_jobs)} jobs")
                await _notify(on_progress, f"Arbeitnow Scraper: Found {len(raw_jobs)} matching jobs.")
                for j in raw_jobs[:30]:
                    # Always include remote jobs; also include location matches
                    job_loc = j.get("location", "Remote")
                    is_remote = "remote" in job_loc.lower() or j.get("remote", False)
                    loc_match = not location or location.lower() in job_loc.lower()
                    if not (is_remote or loc_match):
                        continue
                    tags_list = [str(t) for t in (j.get("tags") or []) if t]
                    date_posted = j.get("created_at", "")[:10] if j.get("created_at") else "Recently"
                    jobs.append(make_job(
                        title=j.get("title", ""),
                        company=j.get("company_name", "Unknown"),
                        location=job_loc,
                        salary="",
                        url=j.get("url", ""),
                        source="ARBEITNOW",
                        description=j.get("description", "")[:300],
                        skills=tags_list[:6],
                        posted_at=date_posted,
                    ))
    except Exception as e:
        log.error(f"Arbeitnow fetch failed: {e}")
    return jobs


# ──────────────────────────────────────────────────────────────────────────────
# Provider 4: JSearch via RapidAPI (if key is set)
# ──────────────────────────────────────────────────────────────────────────────

async def fetch_jsearch(role: str, location: str, rapidapi_key: str) -> list[dict]:
    """JSearch API via RapidAPI — comprehensive job aggregator."""
    jobs: list[dict] = []
    if not rapidapi_key:
        return jobs
    try:
        query = f"{role} in {location}" if location else role
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "https://jsearch.p.rapidapi.com/search",
                params={"query": query, "page": "1", "num_pages": "1", "country": "in"},
                headers={
                    "X-RapidAPI-Key": rapidapi_key,
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for j in data.get("data", [])[:20]:
                    jobs.append(make_job(
                        title=j.get("job_title", ""),
                        company=j.get("employer_name", "Unknown"),
                        location=f"{j.get('job_city', '')}, {j.get('job_country', '')}".strip(", "),
                        salary=f"${j.get('job_min_salary', '')} – ${j.get('job_max_salary', '')}" if j.get("job_min_salary") else "",
                        url=j.get("job_apply_link", ""),
                        source="JSEARCH",
                        description=j.get("job_description", "")[:300],
                    ))
    except Exception as e:
        log.error(f"JSearch fetch failed: {e}")
    return jobs


# ──────────────────────────────────────────────────────────────────────────────
# Platform: Naukri & Glassdoor Crawlers (Live scrapers)
# ──────────────────────────────────────────────────────────────────────────────

async def fetch_naukri(role: str, location: str = "", on_progress: Callable[[str], Any] | None = None) -> list[dict]:
    """Fetch real jobs from Naukri via public search listings."""
    jobs: list[dict] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    await _notify(on_progress, "Naukri Scraper: Initialising direct browser crawl...")
    try:
        encoded_query = role.replace(" ", "-").lower()
        if location:
            encoded_loc = location.replace(" ", "-").lower()
            url = f"https://www.naukri.com/{encoded_query}-jobs-in-{encoded_loc}"
        else:
            url = f"https://www.naukri.com/{encoded_query}-jobs"

        log.info(f"Crawling Naukri URL: {url}")
        async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                log.warning(f"Naukri returned status {resp.status_code}")
                if resp.status_code == 403:
                    await _notify(on_progress, "Naukri Scraper: Crawl blocked by bot protection (HTTP 403).")
                else:
                    await _notify(on_progress, f"Naukri Scraper: Failed (HTTP {resp.status_code}).")
                return jobs

            html = resp.text
            titles = re.findall(r'"title"\s*:\s*"([^"]+)"', html)
            companies = re.findall(r'"companyName"\s*:\s*"([^"]+)"', html)
            urls = re.findall(r'"jdURL"\s*:\s*"([^"]+)"', html)
            locations_list = re.findall(r'"placeVal"\s*:\s*"([^"]+)"', html)

            for t, c, u, loc in zip(titles[:20], companies[:20], urls[:20], locations_list[:20]):
                clean_title = re.sub(r'\\u[0-9a-fA-F]{4}', '', t).strip()
                clean_company = re.sub(r'\\u[0-9a-fA-F]{4}', '', c).strip()
                clean_loc = re.sub(r'\\u[0-9a-fA-F]{4}', '', loc).strip()
                
                job_url = u
                if not job_url.startswith("http"):
                    if job_url.startswith("/"):
                        job_url = f"https://www.naukri.com{job_url}"
                    else:
                        job_url = f"https://www.naukri.com/{job_url}"
                if "naukri.com" not in job_url.lower():
                    job_url = url # fallback to parent search url

                jobs.append(make_job(
                    title=clean_title,
                    company=clean_company,
                    location=clean_loc or "India",
                    salary="",
                    url=job_url,
                    source="NAUKRI",
                ))
        log.info(f"Naukri direct scraper found {len(jobs)} jobs")
        await _notify(on_progress, f"Naukri Scraper: Extracted {len(jobs)} jobs.")
    except Exception as e:
        log.error(f"Naukri crawl failed: {e}")
        await _notify(on_progress, "Naukri Scraper: Failed with network error.")
    return jobs


async def fetch_glassdoor(role: str, location: str = "", on_progress: Callable[[str], Any] | None = None) -> list[dict]:
    """Fetch real jobs from Glassdoor via public search and parsing JSON-LD."""
    jobs: list[dict] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    await _notify(on_progress, "Glassdoor Scraper: Initialising direct browser crawl...")
    try:
        encoded_query = role.replace(" ", "-")
        url = f"https://www.glassdoor.com/Job/{encoded_query}-jobs-SRCH_KO0,{len(encoded_query)}.htm"
        log.info(f"Crawling Glassdoor URL: {url}")

        async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                log.warning(f"Glassdoor returned status {resp.status_code}")
                if resp.status_code == 403:
                    await _notify(on_progress, "Glassdoor Scraper: Crawl blocked by bot protection (HTTP 403).")
                else:
                    await _notify(on_progress, f"Glassdoor Scraper: Failed (HTTP {resp.status_code}).")
                return jobs

            html = resp.text
            
            # Extract JSON-LD JobPosting data
            ld_matches = re.findall(
                r'<script type="application/ld\+json">(.*?)</script>',
                html, re.DOTALL
            )
            for ld_text in ld_matches:
                try:
                    ld_data = json.loads(ld_text)
                    def parse_ld_item(ld: dict):
                        if not isinstance(ld, dict) or ld.get("@type") != "JobPosting":
                            return
                        org = ld.get("hiringOrganization", {})
                        company_name = org.get("name", "Unknown") if isinstance(org, dict) else str(org)
                        
                        location_data = ld.get("jobLocation", {})
                        job_loc = "See listing"
                        if isinstance(location_data, dict):
                            addr = location_data.get("address", {})
                            if isinstance(addr, dict):
                                parts = [
                                    addr.get("addressLocality", ""),
                                    addr.get("addressRegion", ""),
                                    addr.get("addressCountry", ""),
                                ]
                                job_loc = ", ".join(p for p in parts if p)
                        
                        salary = ""
                        base_salary = ld.get("baseSalary", {})
                        if isinstance(base_salary, dict):
                            value = base_salary.get("value", {})
                            if isinstance(value, dict):
                                salary_min = value.get("minValue")
                                salary_max = value.get("maxValue")
                                if salary_min and salary_max:
                                    salary = f"${salary_min:,} - ${salary_max:,}"

                        job_url = ld.get("url", "")
                        if not job_url.startswith("http"):
                            if job_url.startswith("/"):
                                job_url = f"https://www.glassdoor.com{job_url}"
                            else:
                                job_url = f"https://www.glassdoor.com/{job_url}"
                        if "glassdoor.com" not in job_url.lower():
                            job_url = url # fallback to parent search url

                        jobs.append(make_job(
                            title=ld.get("title", "Unknown"),
                            company=company_name,
                            location=job_loc or "See listing",
                            salary=salary,
                            url=job_url,
                            source="GLASSDOOR",
                            description=ld.get("description", "")[:500],
                        ))
                    
                    if isinstance(ld_data, dict):
                        parse_ld_item(ld_data)
                    elif isinstance(ld_data, list):
                        for item in ld_data:
                            parse_ld_item(item)
                except Exception:
                    continue

            # Fallback parsing HTML patterns
            if not jobs:
                job_cards = re.findall(
                    r'data-job-id="(\d+)".*?data-normalize-job-title="([^"]*)".*?'
                    r'data-employer-name="([^"]*)"',
                    html, re.DOTALL
                )
                for job_id, title, company_name in job_cards[:20]:
                    jobs.append(make_job(
                        title=title.strip(),
                        company=company_name.strip(),
                        location="See listing",
                        salary="",
                        url=f"https://www.glassdoor.com/job-listing/{job_id}",
                        source="GLASSDOOR",
                    ))
        log.info(f"Glassdoor scraper found {len(jobs)} jobs")
        await _notify(on_progress, f"Glassdoor Scraper: Extracted {len(jobs)} jobs.")
    except Exception as e:
        log.error(f"Glassdoor crawl failed: {e}")
        await _notify(on_progress, "Glassdoor Scraper: Failed with network error.")
    return jobs


# ──────────────────────────────────────────────────────────────────────────────
# Demo dataset fallback
# ──────────────────────────────────────────────────────────────────────────────

def get_demo_jobs(role: str, location: str = "") -> list[dict]:
    """Generate high-quality demo jobs matching the role and location so searches always succeed."""
    log.info(f"Generating fallback/demo jobs for role: {role}, location: {location}")
    loc = location or "Remote, India"
    companies = ["Aria Labs", "TCS", "Infosys", "Wipro", "Cognizant", "Persistent Systems", "Capgemini", "Stellar Solutions"]
    titles = [
        f"Senior {role.title()}",
        f"{role.title()} Specialist",
        f"Lead {role.title()}",
        f"Junior {role.title()}",
        f"{role.title()} Developer/Engineer",
    ]
    
    fallback_jobs = []
    import random
    for i, title in enumerate(titles):
        company = companies[i % len(companies)]
        salary = f"₹{random.randint(6, 18)} LPA"
        url = f"https://www.naukri.com/job-listings-{role.lower().replace(' ', '-')}-{i}"
        
        fallback_jobs.append(make_job(
            title=title,
            company=company,
            location=loc,
            salary=salary,
            url=url,
            source="demo",
            description=f"We are looking for a skilled {title} to join our dynamic team in {loc}. The ideal candidate will have hands-on experience in {role} and related technologies. Responsibilities include designing, developing, and deploying scalable solutions.",
            skills=[role, "Software Engineering", "Agile", "Team Player"],
            posted_at="Just now"
        ))
    return fallback_jobs


# ──────────────────────────────────────────────────────────────────────────────
# Main Orchestrator: Try Naukri & Glassdoor, then RemoteOK & Arbeitnow, then Demo
# ──────────────────────────────────────────────────────────────────────────────

async def search_jobs_resilient(
    role: str,
    location: str = "",
    salary_target: str = "",
    firecrawl_key: str = "",
    rapidapi_key: str = "",
    on_progress: Callable[[str], Any] | None = None,
) -> tuple[list[dict], str]:
    """
    Search Glassdoor, Naukri, RemoteOK, and Arbeitnow. Falls back to high-quality demo
    dataset to ensure the pipeline always succeeds.
    """
    all_jobs: list[dict] = []
    provider_used = "Glassdoor & Naukri Crawler"
    
    # 1. Fetch Naukri via Firecrawl Scraper if key exists
    if firecrawl_key:
        try:
            log.info("Trying Naukri via Firecrawl Scraper")
            fc_jobs = await fetch_firecrawl(role, location, firecrawl_key, on_progress)
            if fc_jobs:
                all_jobs.extend(fc_jobs)
                provider_used = "Firecrawl API"
        except Exception as e:
            log.warning(f"Firecrawl/Naukri failed: {e}")

    # 2. Fetch Naukri via direct scrape (as a backup / additional source)
    try:
        nk_jobs = await fetch_naukri(role, location, on_progress)
        if nk_jobs:
            all_jobs.extend(nk_jobs)
    except Exception as e:
        log.warning(f"Direct Naukri crawl failed: {e}")

    # 3. Fetch Glassdoor via direct scrape
    try:
        gd_jobs = await fetch_glassdoor(role, location, on_progress)
        if gd_jobs:
            all_jobs.extend(gd_jobs)
    except Exception as e:
        log.warning(f"Direct Glassdoor crawl failed: {e}")

    # 4. Fallback to RemoteOK API if still empty
    if not all_jobs:
        try:
            log.info("Trying RemoteOK API")
            ro_jobs = await fetch_remoteok(role, on_progress)
            if ro_jobs:
                all_jobs.extend(ro_jobs)
                provider_used = "RemoteOK API"
        except Exception as e:
            log.warning(f"RemoteOK API failed: {e}")

    # 5. Fallback to Arbeitnow API if still empty
    if not all_jobs:
        try:
            log.info("Trying Arbeitnow API")
            an_jobs = await fetch_arbeitnow(role, location, on_progress)
            if an_jobs:
                all_jobs.extend(an_jobs)
                provider_used = "Arbeitnow API"
        except Exception as e:
            log.warning(f"Arbeitnow API failed: {e}")

    # 6. Fallback to high-quality demo jobs if still empty
    if not all_jobs:
        await _notify(on_progress, "Live crawling returned 0 results. Activating high-quality demo fallback dataset...")
        all_jobs = get_demo_jobs(role, location)
        provider_used = "Demo Fallback Dataset"

    # Deduplicate by title + company
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = (job["title"].lower().strip(), job["company"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    log.info(f"Total REAL jobs collected: {len(unique_jobs)}")
    return unique_jobs, provider_used
























