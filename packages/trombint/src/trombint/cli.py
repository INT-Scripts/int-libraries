import argparse
import sys
import os
import json
import logging
from .client import get_students_by_name, get_all_students, get_pfp_by_name, get_all_pfps, download_image

def setup_logging():
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")

def handle_output(students: list[dict], args):
    if not students:
        if args.name:
            print(f"Student '{args.name}' not found.", file=sys.stderr)
        else:
            print("No students found.", file=sys.stderr)
        sys.exit(1)

    # 1. Download images if requested
    if args.download_pfp:
        out_path = args.download_pfp
        if len(students) == 1 and os.path.basename(out_path).endswith(('.jpg', '.jpeg', '.png')):
            # Single student, specific file
            os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.', exist_ok=True)
            url = students[0].get('photo_url')
            if url:
                download_image(url, out_path)
        else:
            # Multiple students or directory specified
            os.makedirs(out_path, exist_ok=True)
            for student in students:
                url = student.get('photo_url')
                if url:
                    uid = student.get('uid', student.get('nom_complet', 'student').replace(' ', '_'))
                    # Clean filename characters if needed
                    safe_uid = "".join(c for c in uid if c.isalnum() or c in ('-', '_'))
                    final_path = os.path.join(out_path, f"{safe_uid}.jpg")
                    download_image(url, final_path)

    # 2. Output JSON info
    if args.pfp_only:
        pfp_urls = [s.get('photo_url') for s in students if s.get('photo_url')]
        if not args.download_pfp: 
            for url in pfp_urls:
                print(url)
    else:
        out_str = json.dumps(students, indent=4, ensure_ascii=False)
        if args.out_json:
            with open(args.out_json, 'w', encoding='utf-8') as f:
                f.write(out_str)
            logging.getLogger("trombint").info(f"Informations sauvegardées dans {args.out_json}")
        else:
            print(out_str)

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(description="TrombINT: A CLI tool and Python module to extract profile pictures and student information from the IMT-BS/TSP directory.")
    parser.add_argument('--name', type=str, help="Search for student(s) by name and get their information.")
    parser.add_argument('--all', action='store_true', help="Get full information for all students.")
    parser.add_argument('--pfp-only', action='store_true', help="Only output the profile picture URL(s) instead of all information.")
    parser.add_argument('--out-json', type=str, help="Path to save the JSON output instead of printing to stdout.")
    parser.add_argument('--download-pfp', type=str, help="Path (file or directory) where the profile picture(s) should be downloaded.")
    
    args = parser.parse_args()

    if args.name:
        students = get_students_by_name(args.name)
        handle_output(students, args)
    elif args.all:
        students = get_all_students()
        handle_output(students, args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
