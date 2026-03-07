import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import getpass
import os
import re
import logging
from typing import Tuple, Dict, Any, Optional
from casint import CASClient

logger = logging.getLogger("agendint")

HEAD = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )
}

START_URL = "https://si-etudiants.imtbs-tsp.eu/OpDotNet/Noyau/Login.aspx?auth=SAMLv2ProviderConfiguration"

class SIClient:
    def __init__(self, cookies: Optional[httpx.Cookies] = None):
        self.cookies = cookies
        self.base_url = None
        self.id_groupe = None
        self.authenticated = False

    async def _get_cookies(self) -> httpx.Cookies:
        if self.cookies: return self.cookies
        cas = await CASClient.get_shared_instance(service_url=START_URL)
        return cas.cookies

    async def get_client(self) -> httpx.AsyncClient:
        cookies = await self._get_cookies()
        return httpx.AsyncClient(cookies=cookies, headers=HEAD, follow_redirects=True)

    @classmethod
    async def create(cls) -> "SIClient":
        instance = cls()
        await instance._finalize_si_login()
        return instance

    async def _handle_js_autosubmit(self, html, base_url, extra_headers=None):
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")
        if not form:
            raise RuntimeError("Pas de formulaire auto-submit trouvé")
        action = urljoin(str(base_url), form.get("action", ""))
        inputs = {inp.get("name"): inp.get("value", "") for inp in form.find_all("input") if inp.get("name")}
        for key in ["shib_idp_ls_supported", "shib_idp_ls_success.shib_idp_session_ss", "shib_idp_ls_success.shib_idp_persistent_ss"]:
            if key in inputs: inputs[key] = "false"
                
        async with await self.get_client() as client:
            r = await client.post(action, data=inputs, headers=extra_headers, timeout=15.0)
            r.raise_for_status()
            # If we don't have local cookies, update the global ones if needed, 
            # but usually SI cookies are session-specific.
            # We keep them in our local state.
            return r

    async def _finalize_si_login(self):
        async with await self.get_client() as client:
            r = await client.get(START_URL, timeout=15.0)
            max_steps = 5
            for _ in range(max_steps):
                if "document.forms[0].submit()" in r.text or "document.formul.submit()" in r.text:
                    r = await self._handle_js_autosubmit(r.text, r.url)
                    continue
                break
                
            self.base_url = str(r.url).rsplit("/", 1)[0] + "/"
            bandeau_url = urljoin(self.base_url, "Bandeau.aspx")
            r_bandeau = await client.get(bandeau_url, timeout=15.0)
            
            if r_bandeau.status_code == 200:
                self.id_groupe = "843"
                match_groupe = re.search(r"var\s+IdGroupe\s*=\s*(\d+);", r_bandeau.text)
                if match_groupe: self.id_groupe = match_groupe.group(1)
                self.authenticated = True
                # Store the resulting SI cookies locally
                self.cookies = client.cookies
            else:
                logger.error(f"Impossible de charger le bandeau (Code: {r_bandeau.status_code})")
                self.authenticated = False

    async def init_agenda_session(self):
        if not self.authenticated or not self.base_url:
             await self._finalize_si_login()
             
        bridge_url = urljoin(self.base_url, "../commun/Login/aspxtoasp.aspx")
        target_url = f"/Eplug/Agenda/Agenda.asp?IdApplication=190&TypeAcces=Utilisateur&IdLien=304&groupe={self.id_groupe}"
        full_bridge_url = f"{bridge_url}?url={target_url}"
        
        async with await self.get_client() as client:
            r = await client.get(full_bridge_url)
            if "document.formul.submit();" in r.text or "aspxtoasp.asp" in r.text:
                 r = await self._handle_js_autosubmit(r.text, r.url)
            self.cookies = client.cookies
            return str(r.url)
