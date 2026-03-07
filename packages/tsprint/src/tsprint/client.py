import requests
from bs4 import BeautifulSoup
import re
import os
import time
import logging
from urllib.parse import urljoin
from .exceptions import LoginError, UploadError, PrinterNotFoundError, JobReleaseError

# Configure logging
logger = logging.getLogger(__name__)

class TSPrintClient:
    """
    A client for interacting with the TSPrint (PaperCut) service.
    
    Attributes:
        username (str): The username for authentication.
        password (str): The password for authentication.
        base_url (str): The base URL of the service.
        session (requests.Session): The HTTP session used for requests.
    """

    def __init__(self, username, password, base_url="https://followme.imtbs-tsp.eu"):
        """
        Initialize the TSPrintClient.

        Args:
            username (str): The username.
            password (str): The password.
            base_url (str, optional): The base URL. Defaults to "https://followme.imtbs-tsp.eu".
        """
        self.username = username
        self.password = password
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self._csrf_token = None

    def get_webprint_printers(self):
        """
        Get the list of available Web Print printers (e.g. Black & White, Color).
        
        Returns:
            list: List of strings (printer names/labels).
        """
        web_print_url = f"{self.base_url}/app?service=page/UserWebPrint"
        r = self._get_page(web_print_url, "Web Print page")
        soup = BeautifulSoup(r.text, 'html.parser')
        
        link = self._find_submit_job_link(soup)
        if not link:
             # If no link, maybe we are already on the printer selection page?
             # But usually we land on the summary page.
             raise UploadError("Could not find 'Envoyer un travail' link.")
             
        action_url = self._resolve_url(link['href'])
        
        # Access Printer Selection page
        r = self._get_page(action_url, "Printer Selection")
        soup = BeautifulSoup(r.text, 'html.parser')
        form = soup.find('form')
        if not form: raise UploadError("No form on Printer Selection page.")

        # Extract printers from radio buttons
        # The labels are usually in a table or list associated with the radio inputs.
        # We need to parse the structure.
        # Typically: <input type="radio" name="$RadioGroup" value="0" ... /> ... <label>Printer Name</label>
        # or inside a table row.
        
        printers = []
        radio_inputs = form.find_all('input', type='radio', attrs={'name': '$RadioGroup'})
        
        for radio in radio_inputs:
             # Find the label or text associated
             # Often it's in a parent 'tr' -> 'td'
             row = radio.find_parent('tr')
             if row:
                 # Look for the cell with the printer name
                 # It might be in a <label> or just text in a <td>
                 # Let's try to get all text in the row and clean it up
                 text = row.get_text(strip=True)
                 # Remove the radio value if present
                 printers.append(text)
             else:
                 # Fallback: check next sibling
                 label = radio.find_next('label')
                 if label:
                     printers.append(label.get_text(strip=True))
                 else:
                     printers.append(f"Printer {radio.get('value')}")
        
        return printers

    def upload_file(self, file_path, copies=1, printer_index=0):
        """
        Upload a file to Web Print.

        Args:
            file_path (str): Path to the file.
            copies (int, optional): Number of copies. Defaults to 1.
            printer_index (int, optional): Index of the printer to select (0 for B&W, 1 for Color usually).

        Raises:
            FileNotFoundError: If file not found.
            UploadError: If upload fails.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Starting upload for {file_path} (Printer Index: {printer_index})...")

        # 1. Access Web Print
        web_print_url = f"{self.base_url}/app?service=page/UserWebPrint"
        r = self._get_page(web_print_url, "Web Print page")
        soup = BeautifulSoup(r.text, 'html.parser')
        
        link = self._find_submit_job_link(soup)
        if not link:
             raise UploadError("Could not find 'Envoyer un travail' link.")
             
        action_url = self._resolve_url(link['href'])
        
        # 2. Printer Selection
        r = self._get_page(action_url, "Printer Selection")
        soup = BeautifulSoup(r.text, 'html.parser')
        form = soup.find('form')
        if not form: raise UploadError("No form on Printer Selection page.")

        data = self._extract_form_data(form)
        data['$RadioGroup'] = str(printer_index) # Select specific printer
        
        # Handle strict button logic
        self._prepare_printer_selection_payload(data, soup)
        self._extract_csrf(r.text)
        
        headers = {'Referer': r.url, 'Origin': self.base_url}
        if self._csrf_token: headers['X-Csrf-Token'] = self._csrf_token

        action_url = self._resolve_url(form.get('action'))
        r = self.session.post(action_url, data=data, headers=headers)
        
        # 3. Options
        soup = BeautifulSoup(r.text, 'html.parser')
        form = soup.find('form')
        if not form: raise UploadError("No form on Options page.")
        
        data = self._extract_form_data(form)
        data['copies'] = str(copies)
        self._prepare_options_payload(data, form)
        
        headers['Referer'] = r.url
        action_url = self._resolve_url(form.get('action'))
        r = self.session.post(action_url, data=data, headers=headers)
        
        # 4. Upload Page
        upload_path = self._find_upload_url(r.text)
        if not upload_path: raise UploadError("Could not find upload URL.")
        
        upload_full_url = self.base_url + upload_path
        files = {'file': (os.path.basename(file_path), open(file_path, 'rb'), 'application/pdf')}
        upload_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': self.base_url,
            'Referer': r.url
        }
        
        r_upload = self.session.post(upload_full_url, files=files, headers=upload_headers)
        if r_upload.status_code != 200:
             raise UploadError(f"Upload failed with status {r_upload.status_code}")
             
        # 5. Finalize
        soup = BeautifulSoup(r.text, 'html.parser')
        final_form = soup.find('form', id='upload-complete') or soup.find('form')
        if not final_form:
            # Maybe the JS submits it? But we need to do it manually.
            pass 
            
        if final_form:
             data = self._extract_form_data(final_form)
             # Remove submits
             submit_keys = [k for k in data if k.startswith('$Submit')]
             for k in submit_keys: del data[k]
             
             action_url = self._resolve_url(final_form.get('action'))
             headers['Referer'] = r.url
             self.session.post(action_url, data=data, headers=headers)
             
        logger.info("Upload sequence completed.")

    def login(self):
        """
        Authenticate with the service.

        Returns:
            bool: True if login is successful.

        Raises:
            LoginError: If login fails.
        """
        logger.info(f"Attempting login for {self.username}...")
        
        login_page_url = f"{self.base_url}/user"
        try:
            r = self.session.get(login_page_url)
            r.raise_for_status()
        except requests.RequestException as e:
            raise LoginError(f"Failed to access login page: {e}")

        # Check if already logged in
        if "Déconnexion" in r.text or "D&#233;connexion" in r.text:
            logger.info("Already logged in.")
            return True

        soup = BeautifulSoup(r.text, 'html.parser')
        form = soup.find('form')
        if not form:
            raise LoginError("No login form found.")

        action = form.get('action')
        action_url = self._resolve_url(action)
        
        data = self._extract_form_data(form)
        data['inputUsername'] = self.username
        data['inputPassword'] = self.password
        
        # Ensure submit button
        submit_btn = form.find('input', type='submit')
        if submit_btn and submit_btn.get('name'):
            data[submit_btn.get('name')] = submit_btn.get('value')
        else:
             data['$Submit$0'] = 'Connexion'

        headers = {'Referer': login_page_url}
        
        try:
            r = self.session.post(action_url, data=data, headers=headers)
        except requests.RequestException as e:
            raise LoginError(f"Login request failed: {e}")

        if "Connexion" in r.text and "inputPassword" in r.text:
             error_msg = "Unknown error"
             soup = BeautifulSoup(r.text, 'html.parser')
             error = soup.find(class_='error') or soup.find(class_='errorMessage')
             if error:
                 error_msg = error.get_text(strip=True)
             raise LoginError(f"Login failed: {error_msg}")
             
        # Verify session
        r_check = self.session.get(f"{self.base_url}/app?service=page/UserSummary")
        if "Connexion" in r_check.text and "inputPassword" in r_check.text:
             raise LoginError("Session check failed after login.")

        logger.info("Login successful.")
        return True




    def get_pending_jobs(self):
        """
        Retrieve pending jobs from the release queue.

        Returns:
            list: List of dicts with job info ('name', 'print_link').
        """
        release_jobs_url = f"{self.base_url}/app?service=page/UserReleaseJobs"
        r = self._get_page(release_jobs_url, "Release Jobs")
        soup = BeautifulSoup(r.text, 'html.parser')
        
        jobs = []
        jobs_table = soup.find('table', id='jobs-table')
        if jobs_table:
            for row in jobs_table.find_all('tr'):
                doc_cell = row.find('td', class_='documentColumnValue')
                if doc_cell:
                    doc_name_span = doc_cell.find('span', class_='smallText')
                    if doc_name_span:
                        filename = doc_name_span.get_text(strip=True)
                        action_cell = row.find('td', class_='actionColumnValue')
                        print_link = None
                        if action_cell:
                            print_btn = action_cell.find('a', string="Imprimer")
                            if print_btn:
                                print_link = print_btn.get('href')
                        
                        if print_link:
                            jobs.append({'name': filename, 'link': print_link})
                            jobs.append({'name': filename, 'link': print_link})
        return jobs

    def get_physical_printers(self, job):
        """
        Get list of physical printers available for releasing the job.
        
        Args:
            job (dict): Job object with 'link' key.
            
        Returns:
            list: List of dicts {'name': str, 'status': str, 'link': str}
        """
        release_url = self._resolve_url(job['link'])
        r = self._get_page(release_url, "Job Release Page")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        printer_links = soup.find_all('a', href=re.compile(r'\$ReleaseStationJobs\.\$DirectLink'))
        
        printers = []
        for link in printer_links:
            row = link.find_parent('tr')
            if row:
                status_cell = row.find_all('td')[-1]
                status_text = status_cell.get_text(strip=True)
                p_name = link.get_text(strip=True)
                printers.append({
                    'name': p_name,
                    'status': status_text,
                    'link': link['href']
                })
        return printers

    def release_job(self, job, printer_name_filter=None):
        """
        Release a specific job.

        Args:
            job (dict): Job object from get_pending_jobs.
            printer_name_filter (str, optional): Substring to match printer name.

        Raises:
            JobReleaseError: If release fails.
        """
        release_url = self._resolve_url(job['link'])
        r = self._get_page(release_url, "Job Release Page")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        printer_links = soup.find_all('a', href=re.compile(r'\$ReleaseStationJobs\.\$DirectLink'))
        
        target_link = None
        available_printers = []
        
        for link in printer_links:
            row = link.find_parent('tr')
            if row:
                status_cell = row.find_all('td')[-1]
                status_text = status_cell.get_text(strip=True)
                p_name = link.get_text(strip=True)
                
                if "OK" in status_text:
                    available_printers.append(p_name)
                    if printer_name_filter:
                        if printer_name_filter.lower() in p_name.lower():
                            target_link = link['href']
                            break
                    else:
                        target_link = link['href']
                        break # Pick first available
        
        if not target_link:
             raise JobReleaseError(f"No available printer found. Available: {available_printers}")
             
        target_url = self._resolve_url(target_link)
        r = self.session.get(target_url)
        if r.status_code != 200:
             raise JobReleaseError(f"Release request failed: {r.status_code}")
             
        logger.info(f"Released job '{job['name']}' to printer.")


    # --- Helpers ---

    def _get_page(self, url, desc):
        r = self.session.get(url)
        if r.status_code != 200:
            raise requests.RequestException(f"Failed to load {desc}: {r.status_code}")
        return r

    def _resolve_url(self, path):
        if not path: return self.base_url
        if path.startswith("http"): return path
        if path.startswith("/"): return self.base_url + path
        return f"{self.base_url}/{path}"

    def _extract_form_data(self, form):
        data = {}
        for input_tag in form.find_all('input'):
            name = input_tag.get('name')
            value = input_tag.get('value', '')
            if name: data[name] = value
        
        for select in form.find_all('select'):
            name = select.get('name')
            if not name: continue
            selected = select.find('option', selected=True)
            if selected:
                data[name] = selected.get('value', '')
            else:
                opts = select.find_all('option')
                if opts: data[name] = opts[0].get('value', '')
        return data

    def _find_submit_job_link(self, soup):
        link = soup.find('a', string=re.compile(r"Envoyer un travail"))
        if not link:
            for a in soup.find_all('a', class_='btn'):
                if "Envoyer un travail" in a.get_text():
                    link = a
                    break
        if not link:
             link = soup.find('a', href=re.compile(r"UserWebPrint.*\$ActionLink"))
        return link

    def _prepare_printer_selection_payload(self, data, soup):
        if '$Hidden' in data: data['$Hidden'] = ''
        if '$Hidden$0' in data: data['$Hidden$0'] = ''
        if '$TextField' in data: data['$TextField'] = ''
        
        keys_to_remove = [k for k in data if k.startswith('$Submit')]
        for k in keys_to_remove: del data[k]
        
        next_btn = soup.find('input', attrs={'name': '$Submit$1'})
        if next_btn:
            data['$Submit$1'] = next_btn.get('value')
        else:
            data['$Submit$1'] = "2. Options d'impression et sélection de compte >>"

    def _extract_csrf(self, text):
        match = re.search(r"var csrfToken = ['\"]([^'\"]+)['\"]", text)
        if match:
            self._csrf_token = match.group(1)

    def _prepare_options_payload(self, data, form):
        submit_keys = [k for k in data if k.startswith('$Submit')]
        for k in submit_keys: 
            if k in data: del data[k]
            
        next_btn = form.find('input', type='submit', value=re.compile(r"Document.*envoyer"))
        if next_btn:
             data[next_btn.get('name')] = next_btn.get('value')
        else:
             data['$Submit'] = "3. Document a envoyer >>"

    def _find_upload_url(self, text):
        upload_match = re.search(r'url\s*:\s*["\'](/upload/\d+)["\']', text)
        if not upload_match:
             upload_match = re.search(r'["\'](/upload/\d+)["\']', text)
        if upload_match:
            return upload_match.group(1)
        return None
