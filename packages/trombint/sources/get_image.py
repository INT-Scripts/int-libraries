import requests

def download_photo_interne(uid):
    # 1. On prépare une session (comme si on ouvrait le navigateur)
    s = requests.Session()
    
    # On se fait passer pour un navigateur classique
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://trombi.imtbs-tsp.eu/etudiants.php'
    })

    print("1. Initialisation de la session (visite de l'annuaire)...")
    # C'est l'étape clé : on va sur la page pour obtenir le cookie "Invité"
    # Sans ça, le serveur refuse de servir la photo
    s.get('https://trombi.imtbs-tsp.eu/etudiants.php')

    # 2. Construction de l'URL
    # Note : Parfois, sans être logué admin, on n'a accès qu'aux vignettes.
    # On essaie d'abord la version HD (sans taille), puis la version vignette si la HD échoue.
    url_hd = f"https://trombi.imtbs-tsp.eu/photo.php?uid={uid}"
    
    print(f"2. Téléchargement de l'image pour : {uid}")
    response = s.get(url_hd)

    # 3. Vérification et Sauvegarde
    if response.status_code == 200:
        # L'image par défaut (silhouette grise) fait souvent moins de 1.5 Ko
        if len(response.content) > 1500:
            filename = f"{uid}.jpg"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✅ Succès : {filename} sauvegardé (Taille: {len(response.content)} octets)")
        else:
            print("⚠️  Attention : L'image téléchargée est très petite.")
            print("   -> C'est probablement la silhouette par défaut.")
            print("   -> Essayez d'ajouter &h=320&w=240 à l'url dans le code si l'école bloque la HD aux invités.")
            
            # Tentative de secours : télécharger la version "vignette" qui est souvent plus permissive
            url_vignette = f"https://trombi.imtbs-tsp.eu/photo.php?uid={uid}&h=320&w=240"
            resp_v = s.get(url_vignette)
            if len(resp_v.content) > 1500:
                 with open(f"{uid}_vignette.jpg", 'wb') as f:
                    f.write(resp_v.content)
                 print(f"✅ Version vignette récupérée à la place.")

    else:
        print(f"❌ Erreur HTTP : {response.status_code}")

# --- Test ---
user_id = input("Entrez l'identifiant (ex: flesieur) : ")
download_photo_interne(user_id)