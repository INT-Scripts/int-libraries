import os
import re
import logging
import httpx
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup
from casint import CASClient
from dotenv import load_dotenv
from typing import Tuple, Dict, Any, Optional, Callable

load_dotenv()

ETUDIANTS_URL = "https://trombi.imtbs-tsp.eu/etudiants.php"

logger = logging.getLogger("trombint")

class TrombINT:
    def __init__(self, cookies: Optional[httpx.Cookies] = None):
        """
        Initializes the TrombINT client.
        """
        self.cookies = cookies
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    async def _get_cookies(self) -> httpx.Cookies:
        if self.cookies: return self.cookies
        # Use shared instance from casint
        cas = await CASClient.get_shared_instance(service_url=ETUDIANTS_URL)
        return cas.cookies

    async def get_client(self) -> httpx.AsyncClient:
        cookies = await self._get_cookies()
        return httpx.AsyncClient(cookies=cookies, headers={"User-Agent": self.user_agent}, follow_redirects=True)

    @classmethod
    async def create(cls) -> "TrombINT":
        """Factory method that ensures CAS is ready."""
        cas = await CASClient.get_shared_instance(service_url=ETUDIANTS_URL)
        return cls(cookies=cas.cookies)

    async def fetch_students_html(self, name: str | None = None) -> str:
        """Fetches the HTML from the trombi etudiants.php page."""
        data = {"etu[user]": name or "", "etu[ecole]": "", "etu[annee]": ""}
        async with await self.get_client() as client:
            response = await client.post(ETUDIANTS_URL, data=data)
            response.raise_for_status()
            return response.text

    def parse_students(self, html_content: str) -> list[dict]:
        """Parses the etudiants HTML and returns a list of dictionaries."""
        soup = BeautifulSoup(html_content, 'html.parser')
        fiches = soup.find_all('div', class_='ldapFiche')
        
        etudiants = []
        for fiche in fiches:
            etudiant = {}
            nom_div = fiche.find('div', class_='ldapNom')
            if nom_div:
                etudiant['nom_complet'] = nom_div.get_text(strip=True)
                
            photo_div = fiche.find('div', class_='ldapPhoto')
            if photo_div:
                link = photo_div.find('a')
                if link and link.get('href'):
                    original_url = link['href']
                    parsed_url = urlparse(original_url)
                    query_params = parse_qs(parsed_url.query)
                    uid = query_params.get('uid', [None])[0]
                    if uid: etudiant['uid'] = uid
                    query_params['h'] = ['320']
                    query_params['w'] = ['240']
                    new_query = urlencode(query_params, doseq=True)
                    new_url = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, new_query, parsed_url.fragment))
                    if not new_url.startswith('http'):
                        new_url = f"https://trombi.imtbs-tsp.eu/{new_url.lstrip('/')}"
                    etudiant['photo_url'] = new_url
                    
            info_div = fiche.find('div', class_='ldapInfo')
            if info_div:
                email_link = info_div.find('a', href=re.compile(r'^mailto:'))
                if email_link: etudiant['email'] = email_link.get_text(strip=True)
                ul = info_div.find('ul')
                if ul:
                    details = [li.get_text(strip=True) for li in ul.find_all('li')]
                    if details: etudiant['details'] = details

            if 'nom_complet' in etudiant:
                etudiants.append(etudiant)
        return etudiants

    async def get_all_students(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> list[dict]:
        if progress_callback: progress_callback(0, 1)
        html = await self.fetch_students_html()
        if progress_callback: progress_callback(1, 1)
        return self.parse_students(html)

    async def get_students_by_name(self, name: str) -> list[dict]:
        html = await self.fetch_students_html(name=name)
        return self.parse_students(html)

    async def download_image(self, url: str, output_path: str):
        headers = {'Referer': ETUDIANTS_URL}
        async with await self.get_client() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)

# Functional API for simpler scripts
async def get_all_students():
    return await (await TrombINT.create()).get_all_students()

async def get_students_by_name(name: str):
    return await (await TrombINT.create()).get_students_by_name(name)

async def download_image(url: str, output_path: str):
    return await (await TrombINT.create()).download_image(url, output_path)
