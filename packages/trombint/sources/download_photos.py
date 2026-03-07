import json
import os
import requests
import time

def download_photos():
    json_file = 'etudiants.json'
    output_dir = 'photos'
    
    # Création du dossier de sortie s'il n'existe pas
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Dossier créé : {output_dir}")

    # Lecture du fichier JSON
    print(f"Lecture du fichier {json_file}...")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            etudiants = json.load(f)
    except FileNotFoundError:
        print(f"❌ Erreur : Le fichier {json_file} est introuvable. Lancez d'abord extract_etudiants.py")
        return

    # Configuration de la session (mêmes headers/cookies que prècédemment)
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://trombi.imtbs-tsp.eu/etudiants.php',
        # On peut ajouter d'autres headers si nécessaire, mais ceux-ci sont généralement suffisants pour les images
        # tant qu'on a le bon cookie de session ci-dessous.
    })
    
    # Cookie de session indispensable
    cookies = {
        'PHPSESSID': '7ac700d66aa0d697511adfef2f59a37b1c769fedd6c98b71b6a72cb2b92640dd'
    }
    session.cookies.update(cookies)

    total = len(etudiants)
    print(f"Début du téléchargement pour {total} étudiants...")

    success_count = 0
    error_count = 0

    for index, etudiant in enumerate(etudiants):
        uid = etudiant.get('uid')
        photo_url = etudiant.get('photo_url')
        
        if not uid or not photo_url:
            print(f"⚠️  Données incomplètes pour l'étudiant #{index+1}")
            continue

        filename = os.path.join(output_dir, f"{uid}.jpg")
        
        # Si l'image existe déjà, on peut choisir de passer (décommenter pour activer)
        # if os.path.exists(filename):
        #     continue

        try:
            response = session.get(photo_url, timeout=10)
            if response.status_code == 200:
                # Vérification contenu minimal (ex: > 100 octets)
                if len(response.content) > 100:
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    # print(f"✅ [{index+1}/{total}] {uid}.jpg téléchargé")
                    success_count += 1
                else:
                    print(f"⚠️  [{index+1}/{total}] {uid} : Image vide ou trop petite")
                    error_count += 1
            else:
                print(f"❌ [{index+1}/{total}] {uid} : Erreur HTTP {response.status_code}")
                error_count += 1
                
        except Exception as e:
            print(f"❌ [{index+1}/{total}] {uid} : Exception - {e}")
            error_count += 1
        
        # Petite pause pour ne pas surcharger le serveur
        time.sleep(0.05) 

    print("\n--- Terminé ---")
    print(f"Succès : {success_count}")
    print(f"Erreurs : {error_count}")

if __name__ == "__main__":
    download_photos()
