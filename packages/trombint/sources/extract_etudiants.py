from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def extract_etudiants():
    input_file = 'etudiants.html'
    output_file = 'etudiants.json'
    
    print(f"Lecture du fichier {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"❌ Erreur : Le fichier {input_file} est introuvable.")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    
    etudiants = []
    
    # Trouver toutes les fiches (class "ldapFiche")
    fiches = soup.find_all('div', class_='ldapFiche')
    print(f"Nombre de fiches trouvées : {len(fiches)}")

    for fiche in fiches:
        etudiant = {}
        
        # 1. Nom
        nom_div = fiche.find('div', class_='ldapNom')
        if nom_div:
            etudiant['nom_complet'] = nom_div.get_text(strip=True)
        
        # 2. Photo URL (et UID)
        photo_div = fiche.find('div', class_='ldapPhoto')
        if photo_div:
            link = photo_div.find('a')
            if link and link.get('href'):
                original_url = link['href']
                
                # Parsing de l'URL pour s'assurer des paramètres h et w
                parsed_url = urlparse(original_url)
                query_params = parse_qs(parsed_url.query)
                
                # Extraction de l'UID
                uid = query_params.get('uid', [None])[0]
                if uid:
                    etudiant['uid'] = uid
                
                # Force les paramètres h=320 et w=240
                query_params['h'] = ['320']
                query_params['w'] = ['240']
                
                # Reconstruction de l'URL
                new_query = urlencode(query_params, doseq=True)
                new_url = urlunparse((
                    parsed_url.scheme, 
                    parsed_url.netloc, 
                    parsed_url.path, 
                    parsed_url.params, 
                    new_query, 
                    parsed_url.fragment
                ))
                etudiant['photo_url'] = new_url
        
        # 3. Informations supplémentaires (Email, Statut, etc.)
        info_div = fiche.find('div', class_='ldapInfo')
        if info_div:
            # Email
            email_link = info_div.find('a', href=re.compile(r'^mailto:'))
            if email_link:
                etudiant['email'] = email_link.get_text(strip=True)
            
            # Autres infos (souvent dans des <ul><li>)
            # Exemple: <ul><li>Ingénieur 1ère année</li></ul>
            ul = info_div.find('ul')
            if ul:
                details = [li.get_text(strip=True) for li in ul.find_all('li')]
                if details:
                    etudiant['details'] = details

        etudiants.append(etudiant)

    # Sauvegarde en JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(etudiants, f, ensure_ascii=False, indent=4)
    
    print(f"✅ Extraction terminée. {len(etudiants)} étudiants sauvegardés dans {output_file}")

if __name__ == "__main__":
    extract_etudiants()
