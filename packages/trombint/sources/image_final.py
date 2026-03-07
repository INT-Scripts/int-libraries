import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urlparse, parse_qs

# Configuration
payload = {
    'etu[user]': 'Timothé',
    'etu[ecole]': 'TSP',
    'etu[annee]': 'fi_1',
}

os.makedirs('photos', exist_ok=True)

# Session avec Headers complets (importants !)
s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://trombi.imtbs-tsp.eu/etudiants.php'
})

print("1. Initialisation...")
# On récupère le cookie initial
s.get('https://trombi.imtbs-tsp.eu/etudiants.php')

print("2. Recherche...")
response = s.post('https://trombi.imtbs-tsp.eu/etudiants.php', data=payload)

# Vérification qu'on est pas redirigé vers le login (cas6...)
if "cas6.imtbs-tsp.eu" in response.url:
    print("ERREUR: Le script a été redirigé vers le login CAS. Tu n'es pas reconnu comme étant sur le réseau interne pour cette requête.")
    exit()

soup = BeautifulSoup(response.content, 'html.parser')
fiches = soup.find_all('div', class_='ldapFiche')

print(f"-> {len(fiches)} étudiants trouvés.")

etudiants = []

for fiche in fiches:
    try:
        nom = fiche.find('div', class_='ldapNom').get_text(strip=True)
        img_tag = fiche.find('img')
        
        if not img_tag:
            print(f"Pas d'image pour {nom}")
            continue

        # Extraction propre de l'UID
        src = img_tag['src']
        parsed = urlparse(src)
        uid = parse_qs(parsed.query).get('uid', ['inconnu'])[0]
        
        # URL de téléchargement HD
        photo_url = f"https://trombi.imtbs-tsp.eu/photo.php?uid={uid}"
        
        print(f"Téléchargement : {nom} ({uid})...")
        
        # On télécharge
        img_resp = s.get(photo_url)
        
        if img_resp.status_code == 200 and len(img_resp.content) > 1000:
            filename = f"photos/{uid}.jpg"
            with open(filename, "wb") as f:
                f.write(img_resp.content)
            photo_path = filename
        else:
            print(f"   ⚠️ Image vide ou erreur pour {uid}")
            photo_path = None

        etudiants.append({
            'uid': uid,
            'nom': nom,
            'photo': photo_path
        })
        
    except Exception as e:
        print(f"Erreur sur une fiche : {e}")

# Sauvegarde JSON
with open('resultats.json', 'w', encoding='utf-8') as f:
    json.dump(etudiants, f, indent=4, ensure_ascii=False)

print("Terminé.")

# CE PROGRAMM NE FONCTIONNE QUE SUR LE RESEAU (GENRE MINET CA FONCTIONNE)
# DE L'IMTBS TSP, CAR LE TROMBI N'EST PAS ACCESSIBLE DEPUIS L'EXTERIEUR.