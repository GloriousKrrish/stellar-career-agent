"""
Agent 4 — Job Discovery Agent

Searches ONLY real job boards:
  - weworkremotely.com
  - glassdoor.com

NO AI-generated fake jobs. NO fallback synthetic data.
If no jobs are found, returns an empty list.
"""
from __future__ import annotations
import asyncio
import json
import re
import uuid
from datetime import datetime
from typing import Any, Callable
from html import unescape

import httpx
import google.generativeai as genai

from config import get_settings
from logger import get_logger
from models import CareerProfile, RawJob, UserProfile

log = get_logger("JobDiscoveryAgent")
settings = get_settings()


class JobDiscoveryAgent:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        log.info("JobDiscoveryAgent initialised — sources: weworkremotely.com, glassdoor.com")

    def _clean_html(self, text: str) -> str:
        """Strip HTML tags and unescape entities."""
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = unescape(clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean[:1000]

    # ── WeWorkRemotely ────────────────────────────────────────────────────────

    async def _fetch_weworkremotely(self, query: str) -> list[RawJob]:
        """Fetch jobs from WeWorkRemotely RSS feed."""
        jobs: list[RawJob] = []
        categories = [
            "remote-jobs/programming",
            "remote-jobs/design",
            "remote-jobs/devops-sysadmin",
            "remote-jobs/management-finance",
            "remote-jobs/customer-support",
            "remote-jobs/sales-marketing",
            "remote-jobs/product",
        ]
        query_lower = query.lower()
        headers = {
            "User-Agent": "StellarCareerAgent/2.0 (job search aggregator)",
            "Accept": "application/rss+xml, application/xml, text/xml",
        }

        try:
            async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
                for category in categories:
                    try:
                        url = f"https://weworkremotely.com/categories/{category}.rss"
                        resp = await client.get(url)
                        if resp.status_code != 200:
                            continue

                        xml_text = resp.text
                        # Parse RSS items manually (avoid lxml dependency)
                        items = re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL)

                        for item_xml in items:
                            title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item_xml)
                            if not title_m:
                                title_m = re.search(r"<title>(.*?)</title>", item_xml)
                            link_m = re.search(r"<link>(.*?)</link>", item_xml)
                            desc_m = re.search(r"<description><!\[CDATA\[(.*?)\]\]></description>", item_xml, re.DOTALL)
                            pubdate_m = re.search(r"<pubDate>(.*?)</pubDate>", item_xml)

                            if not title_m:
                                continue

                            raw_title = self._clean_html(title_m.group(1))

                            # WeWorkRemotely titles are often "Company: Job Title"
                            company = "Unknown"
                            title = raw_title
                            if ":" in raw_title:
                                parts = raw_title.split(":", 1)
                                company = parts[0].strip()
                                title = parts[1].strip()

                            # Filter by query relevance
                            full_text = f"{title} {company} {desc_m.group(1) if desc_m else ''}".lower()
                            if query_lower and not any(
                                term in full_text
                                for term in query_lower.split()
                            ):
                                continue

                            description = ""
                            if desc_m:
                                description = self._clean_html(desc_m.group(1))

                            link = link_m.group(1) if link_m else ""
                            if link and not link.startswith("http"):
                                link = "https://weworkremotely.com" + link

                            posted_at = pubdate_m.group(1) if pubdate_m else "Recently"

                            jobs.append(RawJob(
                                id=str(uuid.uuid4()),
                                title=title,
                                company=company,
                                location="Remote",
                                remote="Remote",
                                salary="",
                                description=description,
                                skills=[],
                                url=link,
                                source="weworkremotely.com",
                                posted_at=posted_at,
                                industry=category.split("/")[-1].replace("-", " ").title(),
                            ))

                        await asyncio.sleep(0.3)  # rate limit

                    except Exception as e:
                        log.warning(f"WWR category {category} failed: {e}")
                        continue

        except Exception as e:
            log.error(f"WeWorkRemotely fetch failed: {e}")

        log.info(f"WeWorkRemotely: found {len(jobs)} jobs for query '{query}'")
        return jobs

    # ── Glassdoor ─────────────────────────────────────────────────────────────

    async def _fetch_glassdoor(self, query: str) -> list[RawJob]:
        """
        Fetch jobs from Glassdoor via their public job listing pages.
        Glassdoor does not have a free public API, so we scrape their
        job search page and extract structured data.
        """
        jobs: list[RawJob] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            encoded_query = query.replace(" ", "-")
            url = f"https://www.glassdoor.com/Job/{encoded_query}-jobs-SRCH_KO0,{len(encoded_query)}.htm"

            async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    log.warning(f"Glassdoor returned status {resp.status_code}")
                    return jobs

                html = resp.text

                # Extract job data from Glassdoor's structured data / JSON-LD
                ld_matches = re.findall(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    html, re.DOTALL
                )
                for ld_text in ld_matches:
                    try:
                        ld_data = json.loads(ld_text)
                        if isinstance(ld_data, dict) and ld_data.get("@type") == "JobPosting":
                            self._parse_glassdoor_ld(ld_data, jobs)
                        elif isinstance(ld_data, list):
                            for item in ld_data:
                                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                                    self._parse_glassdoor_ld(item, jobs)
                    except json.JSONDecodeError:
                        continue

                # Fallback: parse from the HTML page patterns
                if not jobs:
                    job_cards = re.findall(
                        r'data-job-id="(\d+)".*?data-normalize-job-title="([^"]*)".*?'
                        r'data-employer-name="([^"]*)"',
                        html, re.DOTALL
                    )
                    for job_id, title, company in job_cards[:20]:
                        jobs.append(RawJob(
                            id=str(uuid.uuid4()),
                            title=self._clean_html(title),
                            company=self._clean_html(company),
                            location="See listing",
                            remote="Onsite",
                            salary="",
                            description="",
                            skills=[],
                            url=f"https://www.glassdoor.com/job-listing/{job_id}",
                            source="glassdoor.com",
                            posted_at="Recently",
                        ))

        except Exception as e:
            log.error(f"Glassdoor fetch failed: {e}")

        log.info(f"Glassdoor: found {len(jobs)} jobs for query '{query}'")
        return jobs

    def _parse_glassdoor_ld(self, ld: dict, jobs: list[RawJob]):
        """Parse a JSON-LD JobPosting into a RawJob."""
        try:
            org = ld.get("hiringOrganization", {})
            company = org.get("name", "Unknown") if isinstance(org, dict) else str(org)

            location_data = ld.get("jobLocation", {})
            location = "See listing"
            if isinstance(location_data, dict):
                addr = location_data.get("address", {})
                if isinstance(addr, dict):
                    parts = [
                        addr.get("addressLocality", ""),
                        addr.get("addressRegion", ""),
                        addr.get("addressCountry", ""),
                    ]
                    location = ", ".join(p for p in parts if p)

            salary = ""
            salary_min = 0
            salary_max = 0
            base_salary = ld.get("baseSalary", {})
            if isinstance(base_salary, dict):
                value = base_salary.get("value", {})
                if isinstance(value, dict):
                    salary_min = int(value.get("minValue", 0) or 0)
                    salary_max = int(value.get("maxValue", 0) or 0)
                    if salary_min and salary_max:
                        salary = f"${salary_min:,} - ${salary_max:,}"

            remote_type = "Onsite"
            job_loc_type = ld.get("jobLocationType", "")
            if "remote" in str(job_loc_type).lower() or "remote" in location.lower():
                remote_type = "Remote"

            job_url = ld.get("url", "")
            if not job_url.startswith("http"):
                if job_url.startswith("/"):
                    job_url = f"https://www.glassdoor.com{job_url}"
                else:
                    job_url = f"https://www.glassdoor.com/{job_url}"
            if "glassdoor.com" not in job_url.lower():
                job_url = "https://www.glassdoor.com"

            jobs.append(RawJob(
                id=str(uuid.uuid4()),
                title=ld.get("title", "Unknown"),
                company=company,
                location=location or "See listing",
                remote=remote_type,
                salary=salary,
                salary_min=salary_min,
                salary_max=salary_max,
                description=self._clean_html(ld.get("description", ""))[:500],
                skills=[],
                url=job_url,
                source="glassdoor.com",
                posted_at=ld.get("datePosted", "Recently"),
                industry=ld.get("industry", ""),
            ))
        except Exception as e:
            log.warning(f"Failed to parse Glassdoor JSON-LD: {e}")

    # ── Naukri ────────────────────────────────────────────────────────────────

    async def _fetch_naukri(self, query: str) -> list[RawJob]:
        """
        Fetch jobs from Naukri via public job search listings.
        """
        jobs: list[RawJob] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            encoded_query = query.replace(" ", "-").lower()
            url = f"https://www.naukri.com/{encoded_query}-jobs"

            async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    log.warning(f"Naukri returned status {resp.status_code}")
                    return jobs

                html = resp.text

                # Extract jobs using regex from window._initialState or script tags
                titles = re.findall(r'"title"\s*:\s*"([^"]+)"', html)
                companies = re.findall(r'"companyName"\s*:\s*"([^"]+)"', html)
                urls = re.findall(r'"jdURL"\s*:\s*"([^"]+)"', html)
                locations = re.findall(r'"placeVal"\s*:\s*"([^"]+)"', html)

                for t, c, u, loc in zip(titles[:20], companies[:20], urls[:20], locations[:20]):
                    job_url = u
                    if not job_url.startswith("http"):
                        if job_url.startswith("/"):
                            job_url = f"https://www.naukri.com{job_url}"
                        else:
                            job_url = f"https://www.naukri.com/{job_url}"
                    if "naukri.com" not in job_url.lower():
                        job_url = url # fallback to parent search url

                    jobs.append(RawJob(
                        id=str(uuid.uuid4()),
                        title=self._clean_html(t),
                        company=self._clean_html(c),
                        location=self._clean_html(loc) or "Remote/India",
                        remote="Remote" if "remote" in loc.lower() else "Onsite",
                        salary="",
                        description="",
                        skills=[],
                        url=job_url,
                        source="naukri.com",
                        posted_at="Recently",
                    ))

        except Exception as e:
            log.error(f"Naukri fetch failed: {e}")

        log.info(f"Naukri: found {len(jobs)} jobs for query '{query}'")
        return jobs

    # ── AI Enrichment (NOT generation) ────────────────────────────────────────

    async def _enrich_jobs_with_ai(self, jobs: list[RawJob], career: CareerProfile) -> list[RawJob]:
        """Use Gemini to extract skills and categorize REAL jobs. Does NOT create fake jobs."""
        if not jobs:
            return jobs

        jobs_data = [{"title": j.title, "company": j.company, "description": j.description[:200]} for j in jobs[:15]]
        jobs_json = json.dumps(jobs_data, indent=2)

        prompt = f"""Analyze these REAL job listings and extract structured data.
For each job, return skills, experience level, and industry.

Jobs to analyze:
{jobs_json}

Return ONLY valid JSON array (no markdown):
[
  {{
    "index": 0,
    "skills": ["skill1", "skill2"],
    "experience": "Entry|Mid|Senior|Staff|Principal",
    "industry": "Technology|Finance|Healthcare|etc"
  }}
]
"""
        try:
            response = await self.model.generate_content_async(prompt)
            clean = re.sub(r"```(?:json)?", "", response.text).replace("```", "").strip()
            enrichments = json.loads(clean) if clean.startswith("[") else []

            for item in enrichments:
                idx = item.get("index", -1)
                if 0 <= idx < len(jobs):
                    jobs[idx].skills = item.get("skills", [])
                    jobs[idx].experience = item.get("experience", "Mid")
                    jobs[idx].industry = item.get("industry", "")
        except Exception as e:
            log.warning(f"AI enrichment failed (non-critical): {e}")

        return jobs

    # ── Main Discovery ────────────────────────────────────────────────────────

    async def discover(
        self,
        user_profile: UserProfile,
        career: CareerProfile,
        role: str = "",
        remote_preference: str = "Remote",
        limit: int = 20,
        on_progress: Callable[[str], Any] | None = None,
    ) -> list[RawJob]:
        """
        Discover REAL jobs from weworkremotely.com, glassdoor.com, and naukri.com.
        Uses resilient multi-provider search (including Firecrawl API).
        """
        query = role or (career.ideal_titles[0] if career.ideal_titles else "engineer")
        log.info(f"Starting REAL job discovery for '{query}' | user={user_profile.name}")

        from job_providers import search_jobs_resilient

        loc = user_profile.location or ""
        salary_target_str = ""
        if career.salary_min:
            salary_target_str = f"₹{career.salary_min // 100000} LPA"

        raw_list, provider = await search_jobs_resilient(
            role=query,
            location=loc,
            salary_target=salary_target_str,
            firecrawl_key=settings.firecrawl_api_key,
            rapidapi_key="",
            on_progress=on_progress,
        )

        all_jobs: list[RawJob] = []
        for item in raw_list:
            rem = item.get("remote", "Onsite")
            if rem not in ["Remote", "Hybrid", "Onsite"]:
                rem = "Remote" if "remote" in str(item.get("location", "")).lower() else "Onsite"

            job_url = item.get("url") or ""
            source_lower = str(item.get("source", "")).lower()

            # Validation step to ensure URLs don't bleed out
            if "naukri" in source_lower:
                if "naukri.com" not in job_url.lower():
                    # Fallback to general Naukri search page or ignore
                    job_url = f"https://www.naukri.com/{query.replace(' ', '-').lower()}-jobs"
            elif "glassdoor" in source_lower:
                if "glassdoor.com" not in job_url.lower():
                    # Fallback to general Glassdoor search page or ignore
                    job_url = f"https://www.glassdoor.com/Job/{query.replace(' ', '-').lower()}-jobs.htm"

            all_jobs.append(RawJob(
                id=item.get("id") or str(uuid.uuid4()),
                title=item.get("title", "Unknown"),
                company=item.get("company", "Unknown"),
                location=item.get("location") or "See listing",
                remote=rem,
                salary=item.get("salary") or "Undisclosed",
                description=item.get("description") or "No description provided.",
                skills=item.get("skills") or [],
                url=job_url,
                source=item.get("source") or "Web",
                posted_at=item.get("posted_at") or "Recently",
            ))

        # Enrich real jobs with AI-extracted skills (does NOT create fake jobs)
        if all_jobs:
            all_jobs = await self._enrich_jobs_with_ai(all_jobs, career)

        log.info(f"Total REAL jobs discovered: {len(all_jobs)} from {provider}")
        return all_jobs[:limit]

