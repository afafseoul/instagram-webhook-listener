def fetch_page_ids():
    print("⚙️ Mode test : utilisation des IDs en dur")

    page_ids = [
        {
            "page_id": "17841464324220975",  # Page Gestion J-C
            "instagram_id": "17850965606804656",  # Remplace par l'ID Instagram réel
            "client_name": "Gestion J-C"
        },
        {
            "page_id": "17841470887313402",  # Page Gestion J-E
            "instagram_id": "17850965606804656",  # Remplace par l'ID Instagram réel
            "client_name": "Gestion J-E"
        }
    ]

    print(f"✅ Total pages en dur : {len(page_ids)}")
    for entry in page_ids:
        print(f"➡️ Page : {entry['page_id']} - Insta : {entry['instagram_id']} - Client : {entry['client_name']}")
    
    return page_ids

# Pour compatibilité avec les autres modules
get_active_pages = fetch_page_ids
