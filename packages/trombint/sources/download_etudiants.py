import requests

def download_etudiants_page():
    url = 'https://trombi.imtbs-tsp.eu/etudiants.php'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'max-age=0',
        # 'Connection': 'keep-alive', # Managed by requests
        'Referer': 'https://trombi.imtbs-tsp.eu/etudiants.php',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    cookies = {
        'PHPSESSID': '7ac700d66aa0d697511adfef2f59a37b1c769fedd6c98b71b6a72cb2b92640dd'
    }

    print("Téléchargement de la page etudiants.php...")
    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()

        output_file = 'etudiants.html'
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Fichier sauvegardé sous : {output_file}")
        print(f"Taille du fichier : {len(response.content)} octets")

    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la requête : {e}")

if __name__ == "__main__":
    download_etudiants_page()
