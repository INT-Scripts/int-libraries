import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import logging
import getpass
from typing import Tuple, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)

# Shared global instance for session reuse
_shared_client: Optional['CASClient'] = None

class CASClient:
    def __init__(self, service_url: Optional[str] = None, cookies: Optional[httpx.Cookies] = None, user_agent: str = DEFAULT_USER_AGENT):
        """
        Initializes the CAS Client.
        """
        self.cookies = cookies or httpx.Cookies()
        self.user_agent = user_agent
        self.service_url = service_url
        self.authenticated = False
        self.username = None

    def get_client(self) -> httpx.AsyncClient:
        """Returns an httpx.AsyncClient configured with the CAS cookies and User-Agent."""
        return httpx.AsyncClient(cookies=self.cookies, headers={"User-Agent": self.user_agent}, follow_redirects=True)

    @classmethod
    async def get_shared_instance(cls, service_url: str = None) -> 'CASClient':
        """
        Singleton-like accessor to get an authenticated client.
        Prompts for credentials if no shared instance exists and no env vars found.
        """
        global _shared_client
        if _shared_client is None or not _shared_client.authenticated:
            _shared_client = cls(service_url=service_url)
            await _shared_client.login()
        return _shared_client

    @classmethod
    def set_shared_instance(cls, client: 'CASClient'):
        """Manually sets the shared instance (used by orchestrators)."""
        global _shared_client
        _shared_client = client

    def _get_form_data(self, soup: BeautifulSoup) -> Tuple[Optional[str], Dict[str, str]]:
        form = soup.find("form")
        if not form:
            return None, {}
        action = form.get("action", "")
        inputs = {inp.get("name"): inp.get("value", "") for inp in form.find_all("input") if inp.get("name")}
        return action, inputs

    async def login(self, service_url: Optional[str] = None, username: str = None, password: str = None) -> bool:
        """
        Logs in to the CAS service. Prompts interactively if credentials missing.
        """
        target_url = service_url or self.service_url
        if not target_url:
            # Default fallback for school services if none provided
            target_url = "https://si-etudiants.imtbs-tsp.eu/OpDotNet/Noyau/Login.aspx?auth=SAMLv2ProviderConfiguration"

        # Resolve credentials
        if not username: username = os.getenv("CAS_USERNAME") or os.getenv("LOGIN")
        if not password: password = os.getenv("CAS_PASSWORD") or os.getenv("PASSWORD")
            
        if not username:
            username = input("Enter CAS Username: ").strip()
        if not password:
            password = getpass.getpass("Enter CAS Password: ").strip()
        
        self.username = username
        
        logger.info(f"Accessing {target_url}...")
        async with self.get_client() as client:
            try:
                r = await client.get(target_url, timeout=15.0)
                r.raise_for_status()
            except httpx.RequestError as e:
                from .exceptions import CASConnectionError
                raise CASConnectionError(f"Failed to access service URL: {e}") from e

            max_steps = 15
            step = 0
            while step < max_steps:
                step += 1
                soup = BeautifulSoup(r.text, "html.parser")
                
                if "AttributeReleaseRejected" in r.text or soup.find("input", {"name": "_eventId_AttributeReleaseRejected"}):
                    action, inputs = self._get_form_data(soup)
                    msg_inputs = {k: v for k, v in inputs.items() if "AttributeReleaseRejected" not in k and "Cancel" not in k}
                    if "_eventId_proceed" not in msg_inputs: msg_inputs["_eventId_proceed"] = ""
                    r = await client.post(urljoin(str(r.url), action), data=msg_inputs)
                    continue

                password_input = soup.find("input", type="password")
                if password_input:
                    action, inputs = self._get_form_data(soup)
                    inputs["username"] = username
                    inputs["password"] = password
                    next_url = urljoin(str(r.url), action) if action else str(r.url)
                    r = await client.post(next_url, data=inputs)
                    
                    if r.status_code == 200:
                        soup_err = BeautifulSoup(r.text, "html.parser")
                        err = soup_err.find(class_="errors") or soup_err.find(class_="error") or soup_err.find("div", {"class": "alert-danger"}) 
                        if err:
                            from .exceptions import CASLoginError
                            raise CASLoginError(f"Login failed: {err.get_text(strip=True)}")
                    continue

                if "document.forms[0].submit()" in r.text or "document.formul.submit()" in r.text:
                    action, inputs = self._get_form_data(soup)
                    if action or inputs:
                        for key in ["shib_idp_ls_supported", "shib_idp_ls_success.shib_idp_session_ss", "shib_idp_ls_success.shib_idp_persistent_ss"]:
                            if key in inputs: inputs[key] = "false"
                        r = await client.post(urljoin(str(r.url), action), data=inputs)
                        continue

                form = soup.find("form")
                if form:
                     submit_btn = form.find("input", type="submit") or form.find("button", type="submit")
                     if submit_btn or "SAMLRequest" in str(form) or "RelayState" in str(form):
                         action, inputs = self._get_form_data(soup)
                         r = await client.post(urljoin(str(r.url), action), data=inputs)
                         continue
                
                self.authenticated = True
                self.cookies = client.cookies
                return True
            
            from .exceptions import CASLoginError
            raise CASLoginError("Login loop exceeded max steps.")
