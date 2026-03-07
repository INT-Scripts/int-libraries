import asyncio
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import re
import warnings
from typing import List, Optional, Callable
from datetime import date, timedelta
from urllib.parse import urljoin
from .client import SIClient, LIST_CAL_URL
from .models import Calendar, Event

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

async def get_calendars(client: SIClient) -> List[Calendar]:
    if not client.authenticated:
        raise RuntimeError("Client not authenticated")
        
    async with client.get_client() as c:
        r = await c.get(LIST_CAL_URL, timeout=10.0)
        r.raise_for_status()
        html_content = r.text
        
    content_to_parse = html_content
    
    if "parent.MajDivCal" in html_content:
        try:
            start_marker = "parent.MajDivCal('"
            end_marker = "');"
            if start_marker in html_content:
                start_idx = html_content.find(start_marker) + len(start_marker)
                end_idx = html_content.rfind(end_marker)
                if end_idx > start_idx:
                    content_to_parse = html_content[start_idx:end_idx].replace("\\'", "'").replace("\\n", "\n")
        except:
            pass

    soup = BeautifulSoup(content_to_parse, "html.parser")
    found_calendars = []
    
    for element in soup.find_all(True):
        onclick_val = element.get("onclick")
        if onclick_val and "ModCal" in onclick_val:
            match_id = re.search(r"ModCal\('(?P<id>[^']+)'\)", onclick_val)
            if match_id:
                cal_id = match_id.group("id")
                cal_name = element.get_text(strip=True)
                category = "Inconnu"
                if cal_id.startswith("USR"): category = "Utilisateurs"
                elif cal_id.startswith("PRJ"): category = "Projets"
                elif cal_id.startswith("RES"): category = "Ressources"
                
                found_calendars.append(Calendar(id=cal_id, name=cal_name, category=category))
                
    return found_calendars

async def get_events(client: SIClient, calendar_id: str, start_date: date, end_date: date, progress_callback: Optional[Callable[[int, int, date, List[Event]], None]] = None) -> List[Event]:
    if not client.authenticated:
        raise RuntimeError("Client not authenticated")

    real_agenda_url = await client.init_agenda_session()
    all_events = []
    
    def iter_months(s, e):
        curr = s.replace(day=15)
        end = e.replace(day=15)
        while (curr.year, curr.month) <= (end.year, end.month):
            yield curr
            nxt = (curr.replace(day=1) + timedelta(days=32)).replace(day=1)
            curr = nxt.replace(day=15)

    headers = {"Referer": real_agenda_url, "Content-Type": "application/x-www-form-urlencoded"}
    typ_fil_values = ["CNG", "FOR", "69", "68", "33", "RTT", "11899", "11900", "11898", "109", "81", "75", "85", "90", "73", "COU", "106322", "3285", "80", "10121", "20485", "EXA", "111", "82", "77", "78", "84", "76", "89", "4367", "91", "87", "3282", "79", "83", "TD", "4113", "TP", "110", "VIS", "29", "MAL", "MEM", "RDV", "RET", "93", "62", "72", "NON"]

    total_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
    
    current_idx = 0
    async with client.get_client() as c:
        for month_date in iter_months(start_date, end_date):
            current_idx += 1
            if progress_callback:
                progress_callback(current_idx, total_months, month_date, all_events)
                
            date_str = month_date.strftime("%Y%m%d")
            data = {
                "DelEve": "", "NotSup": "", "NumDat": date_str, "DebHor": "07", "FinHor": "20",
                "ValGra": "15", "NomCal": calendar_id, "NumLng": "1", "FromAnn": "NO", "NumApp": "",
                "MLG_BOX21": "del?", "MLG_BOX22": "del?", "MLG_BOX23": "del?", "MLG_BOXNOTIFSUP": "notify?",
                "TxtZom": "100", "TypVis": "Vis-Tab.xsl", "EtaFil": ["NON", "ACT", "ATT"], "TypFil": typ_fil_values
            }
            
            try:
                r = await c.post(real_agenda_url, data=data, headers=headers, timeout=15.0)
                if "document.formul.submit();" in r.text:
                     r = await client._handle_js_autosubmit(r.text, str(r.url), extra_headers=headers)
            except Exception:
                continue
            
            soup = BeautifulSoup(r.text, "html.parser")
            rows = soup.find_all("tr", id="TableDatas")
            if rows:
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 8:
                        nom_div = cols[1].find("div", id="DivNom")
                        nom = nom_div.get_text(strip=True) if nom_div else "Inconnu"
                        type_evt = cols[2].get_text(strip=True)
                        date_evt = cols[4].get_text(strip=True)
                        debut = cols[5].get_text(strip=True)
                        fin = cols[6].get_text(strip=True)
                        
                        nom = nom.replace("\xa0", " ").strip()
                        date_evt = date_evt.replace("\xa0", "").strip()
                        debut = debut.replace("\xa0", "").strip()
                        fin = fin.replace("\xa0", "").strip()
                        
                        evt_id = None
                        row_str = str(row)
                        patterns = [r"Visualiser\('(\d+)'", r"DetEve\('(\d+)'"]
                        for pat in patterns:
                            m_id = re.search(pat, row_str)
                            if m_id:
                                evt_id = m_id.group(1)
                                break
                        
                        try:
                            d_parts = date_evt.split("/")
                            norm_date = f"{d_parts[2]}-{d_parts[1]}-{d_parts[0]}"
                        except:
                            norm_date = date_evt

                        all_events.append(Event(
                            id=evt_id,
                            calendar_id=calendar_id,
                            name=nom, 
                            type=type_evt, 
                            date=norm_date, 
                            start_time=debut, 
                            end_time=fin,
                            raw_time=f"{debut}-{fin}"
                        ))

    return all_events

async def get_event_details(client: SIClient, event: Event, calendar_id: str) -> Event:
    if not event.id: return event

    try:
        await client.init_agenda_session()
    except Exception:
        pass

    det_url = "https://si-etudiants.imtbs-tsp.eu/Eplug/Agenda/Eve-Det.asp"
    params = {
        "NumEve": event.id,
        "DatSrc": event.date.replace("-", ""),
        "NomCal": calendar_id
    }
    
    async with client.get_client() as c:
        try:
            r = await c.get(det_url, params=params, timeout=10.0)
            r.raise_for_status()
        except Exception:
            return event
            
    html_content = r.text
    start_marker = "parent.MajDet('"
    end_marker = "');"
    
    if start_marker not in html_content: return event
    
    start_idx = html_content.find(start_marker) + len(start_marker)
    end_idx = html_content.rfind(end_marker)
    if end_idx <= start_idx: return event
        
    js_content = html_content[start_idx:end_idx]
    clean_html = js_content.replace("\\'", "'").replace("\\/", "/").replace("\\\"","\"")
    soup = BeautifulSoup(clean_html, "html.parser")
    
    details = {}
    title_tag = soup.find("tr", class_="FondMoyen")
    if title_tag:
        details["Titre"] = title_tag.get_text(strip=True).replace("\xa0", " ")

    rows = soup.find_all("tr")
    for row in rows:
        cols = row.find_all("td", class_="GEDcellsouscategorie")
        if len(cols) >= 2:
            key_tag = cols[0].find("b")
            if key_tag:
                key = key_tag.get_text(strip=True).replace(":", "").strip()
                val_col = cols[1]
                links = val_col.find_all("a")
                val_text = val_col.get_text(strip=True).replace("\xa0", " ").strip()
                
                if links:
                    val_list = [a.get_text(strip=True).replace("\xa0", " ") for a in links]
                    details[key] = val_list if len(val_list) > 1 else val_list[0]
                else:
                    details[key] = val_text
                
                if "Etat" in key: event.status = val_text
                elif "Auteur" in key: event.author = val_text
                elif "Formateur" in key: event.trainers = links and [a.get_text(strip=True) for a in links] or [val_text]
                elif "Apprenant" in key: event.students = links and [a.get_text(strip=True) for a in links] or [val_text]
                elif "Projets" in key: event.projects = val_text
                elif "Organismes" in key: event.organisms = links and links[0].get_text(strip=True) or val_text

        room_table = row.find("table", class_="EncadrementPave")
        if room_table:
            r_text = room_table.get_text(strip=True).replace("\xa0", " ").strip()
            event.room = r_text
            details["Salle"] = r_text

    event.full_details = details
    event.details_loaded = True
    return event

async def get_event_details_batch(client: SIClient, events: List[Event], calendar_id: str, concurrency: int = 10) -> List[Event]:
    if not events: return []
    
    try:
        await client.init_agenda_session()
    except:
        pass

    sem = asyncio.Semaphore(concurrency)
    
    async def bound_fetch(evt):
        async with sem:
            return await get_event_details(client, evt, calendar_id)
            
    await asyncio.gather(*(bound_fetch(e) for e in events), return_exceptions=True)
    return events
