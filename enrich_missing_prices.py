import os
import re
import json
import time
import random
import requests
from bs4 import BeautifulSoup
import openpyxl
import urllib.parse

EXCEL_PATH = r"c:\Users\User\Desktop\PYTHON TASKS\gleb\form.xlsx"
OUTPUT_EXCEL_PATH = r"c:\Users\User\Desktop\PYTHON TASKS\gleb\form_enriched.xlsx"
CACHE_PATH = r"c:\Users\User\Desktop\PYTHON TASKS\gleb\scraped_cache.json"
JSON_OUTPUT_PATH = r"c:\Users\User\Desktop\PYTHON TASKS\gleb\data.json"
JS_OUTPUT_PATH = r"c:\Users\User\Desktop\PYTHON TASKS\gleb\data.js"
LOG_PATH = r"c:\Users\User\Desktop\PYTHON TASKS\gleb\scraper_missing.log"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def log_message(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as lf:
        lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    print(msg)

# Clear log
with open(LOG_PATH, "w", encoding="utf-8") as lf:
    lf.write("--- Missing Prices Scraper Started ---\n")

# Load Cache
if os.path.exists(CACHE_PATH):
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)
    log_message(f"Loaded cache with {len(cache)} items.")
else:
    cache = {}
    log_message("No cache found!")

def save_cache():
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def extract_price_from_card(card):
    # Offers tag
    offers_tag = card.find('offers')
    if offers_tag:
        offers_attr = offers_tag.get(':offers')
        if offers_attr:
            try:
                offers_json = json.loads(offers_attr)
                if offers_json:
                    price = offers_json[0].get('price')
                    if price:
                        return int(float(price))
            except Exception: pass
            
    # Retail price match
    card_text = " ".join(card.get_text(separator=' ').split())
    match = re.search(r'Розница\s*([\d\s]+)\s*(?:₽|руб)', card_text)
    if match:
        return int(float(match.group(1).replace(' ', '').replace('\xa0', '')))
        
    # Any price class with digits
    price_elem = card.find(class_=re.compile(r'price', re.I))
    if price_elem:
        price_text = " ".join(price_elem.text.split())
        match = re.search(r'([\d\s]+)\s*(?:₽|руб)', price_text)
        if match:
            return int(float(match.group(1).replace(' ', '').replace('\xa0', '')))
            
    return None

def query_autoopt(search_term):
    url = f"https://www.autoopt.ru/search/index?search={urllib.parse.quote(search_term)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        cards = soup.find_all(lambda tag: tag.name == 'div' and tag.get('class') and 'n-catalog-item' in tag.get('class') and 'n-catalog-item__product' in tag.get('class'))
        
        results = []
        for card in cards:
            link_tag = card.find('a', href=re.compile(r'/catalog/\d+-.+'))
            if not link_tag:
                continue
            href = link_tag.get('href')
            title = link_tag.text.strip()
            price = extract_price_from_card(card)
            results.append({
                "title": title,
                "link": f"https://www.autoopt.ru{href}",
                "price": price
            })
        return results
    except Exception as e:
        log_message(f"Autoopt query exception for '{search_term}': {e}")
        return None

def query_duckduckgo_price(catalog_number, part_name):
    # Formulate a clean query
    query = f"{catalog_number} {part_name} цена"
    # Ensure it's not too long
    query = " ".join(query.split()[:10])
    
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    log_message(f"Querying DuckDuckGo: {query}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            log_message(f"DuckDuckGo search error {r.status_code}")
            return None
            
        soup = BeautifulSoup(r.text, 'html.parser')
        results = soup.find_all(class_='result')
        
        for res in results[:5]:
            title_tag = res.find(class_='result__a')
            snippet_tag = res.find(class_='result__snippet')
            
            title = title_tag.text.strip() if title_tag else ""
            href = title_tag.get('href') if title_tag else ""
            snippet = snippet_tag.text.strip() if snippet_tag else ""
            
            # Unquote real link
            real_link = href
            if href and 'uddg=' in href:
                match = re.search(r'uddg=([^&]+)', href)
                if match:
                    real_link = urllib.parse.unquote(match.group(1))
                    
            # Skip DDG search results or blocks
            if 'duckduckgo.com' in real_link:
                continue
                
            # Regex match price followed by Ruble notation
            price_match = re.search(r'(\d[\d\s\.,]*\d)\s*(?:руб|р\.|₽|рублей|рубля|RUB)', snippet, re.I)
            if price_match:
                price_str = price_match.group(1)
                # Clean decimal part or commas
                price_str = price_str.replace(' ', '').replace('\xa0', '')
                if ',' in price_str or '.' in price_str:
                    # Take the left side of decimal separator
                    price_str = re.split(r'[\.,]', price_str)[0]
                try:
                    price_val = int(price_str)
                    # Check if realistic price
                    if 10 < price_val < 800000:
                        log_message(f"  FOUND on DDG: price={price_val} -> link={real_link}")
                        return {
                            "title": title,
                            "link": real_link,
                            "price": price_val
                        }
                except ValueError:
                    pass
    except Exception as e:
        log_message(f"DuckDuckGo search exception: {e}")
        
    return None

def resolve_part(catalog_str, name_str):
    # Normalizations candidates
    candidates = []
    
    # 1. Shock absorber double-zero normalize
    if '29050' in catalog_str:
        # Replace 29050X with 290500X
        match = re.search(r'29050(\d)', catalog_str)
        if match:
            new_cat = catalog_str.replace(f"29050{match.group(1)}", f"290500{match.group(1)}")
            candidates.append(new_cat)
            
    # 2. Cyrillic to Latin and vice versa (specifically for code letters like A, X, B, C, E, H, M, O, P, T)
    trans_map = str.maketrans("АВЕКМНОРСТХавекмнорстх", "ABEKMHOPCTXabekmhopctx")
    latin_cat = catalog_str.translate(trans_map)
    if latin_cat != catalog_str:
        candidates.append(latin_cat)
        
    trans_map_rev = str.maketrans("ABEKMHOPCTXabekmhopctx", "АВЕКМНОРСТХавекмнорстх")
    cyrillic_cat = catalog_str.translate(trans_map_rev)
    if cyrillic_cat != catalog_str:
        candidates.append(cyrillic_cat)
        
    # 3. Strip spaces (e.g. "0 445 020 224" -> "0445020224")
    no_space_cat = catalog_str.replace(' ', '')
    if no_space_cat != catalog_str:
        candidates.append(no_space_cat)
        
    # 4. Strip trailing letters (e.g. "5297619F" -> "5297619")
    strip_letter_cat = re.sub(r'[a-zA-Zа-яА-Я]$', '', catalog_str)
    if strip_letter_cat != catalog_str and len(strip_letter_cat) >= 4:
        candidates.append(strip_letter_cat)
        
    # Deduplicate candidates while keeping order
    seen = set()
    dedup_candidates = []
    for c in candidates:
        if c not in seen and c != catalog_str:
            dedup_candidates.append(c)
            seen.add(c)
            
    # Search candidates on autoopt first
    for cand in dedup_candidates:
        log_message(f"Searching candidate: '{cand}' on autoopt...")
        results = query_autoopt(cand)
        time.sleep(random.uniform(0.3, 0.6))
        if results:
            best_match = None
            for res in results:
                if res['price'] is not None:
                    best_match = res
                    break
            if not best_match:
                best_match = results[0]
                
            log_message(f"  FOUND candidate on Autoopt: '{best_match['title']}' -> price: {best_match['price']}")
            return {
                "title": best_match['title'],
                "link": best_match['link'],
                "price": best_match['price']
            }
            
    # Search on DDG
    ddg_res = query_duckduckgo_price(catalog_str, name_str)
    time.sleep(random.uniform(0.5, 1.0))
    if ddg_res:
        return ddg_res
        
    return None

def main():
    log_message("Loading workbook for parsing rows...")
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active
    
    header_row = 11
    for r in range(1, 20):
        val = ws.cell(row=r, column=3).value
        if val and "Наименование" in str(val):
            header_row = r
            break
            
    log_message(f"Using header row: {header_row}")
    
    # Identify missing parts
    missing_items = []
    for r in range(header_row + 2, ws.max_row + 1):
        num_val = ws.cell(row=r, column=2).value
        name_val = ws.cell(row=r, column=3).value
        catalog_val = ws.cell(row=r, column=4).value
        
        if num_val is not None:
            try:
                float(num_val)
                cat_str = str(catalog_val).strip() if catalog_val else ""
                
                # Check if it has no price in cache or price is None
                cache_entry = cache.get(cat_str)
                if not cache_entry or cache_entry.get('price') is None:
                    missing_items.append({
                        "row": r,
                        "id": int(float(num_val)),
                        "name": str(name_val).strip() if name_val else "",
                        "catalog": cat_str
                    })
            except ValueError:
                pass
                
    log_message(f"Found {len(missing_items)} missing items to enrich.")
    
    enriched_count = 0
    for idx, item in enumerate(missing_items):
        log_message(f"[{idx+1}/{len(missing_items)}] Processing row {item['row']}: ID={item['id']} | Catalog='{item['catalog']}' | Name='{item['name']}'")
        
        if not item['catalog']:
            log_message("  Skipping: empty catalog number")
            continue
            
        res = resolve_part(item['catalog'], item['name'])
        if res and res['price'] is not None:
            # Update cache
            cache[item['catalog']] = {
                "title": res['title'],
                "link": res['link'],
                "price": res['price']
            }
            save_cache()
            enriched_count += 1
            log_message(f"  --> SUCCESSFULLY ENRICHED! Price: {res['price']}")
        else:
            log_message("  --> Could not enrich this item.")
            
    log_message(f"Enrichment loop completed. Enriched {enriched_count} items.")
    
    # Reload original Excel and rewrite form_enriched.xlsx using the full updated cache
    log_message("Writing final results to Excel...")
    wb_out = openpyxl.load_workbook(EXCEL_PATH)
    ws_out = wb_out.active
    
    # Add link headers
    ws_out.cell(row=header_row, column=7).value = "Ссылка на деталь"
    ws_out.cell(row=header_row+1, column=7).value = "6"
    
    web_data = []
    
    for r in range(header_row + 2, ws_out.max_row + 1):
        num_val = ws_out.cell(row=r, column=2).value
        catalog_val = ws_out.cell(row=r, column=4).value
        name_val = ws_out.cell(row=r, column=3).value
        unit_val = ws_out.cell(row=r, column=5).value
        
        if num_val is not None:
            try:
                float(num_val)
                cat_str = str(catalog_val).strip() if catalog_val else ""
                
                cache_entry = cache.get(cat_str)
                price = None
                link = ""
                
                if cache_entry:
                    price = cache_entry.get('price')
                    link = cache_entry.get('link', '')
                    if not link:
                        link = f"https://www.autoopt.ru/search/index?search={cat_str}"
                else:
                    link = f"https://www.autoopt.ru/search/index?search={cat_str}"
                    
                # Write to Excel cells
                if price is not None:
                    ws_out.cell(row=r, column=6).value = price
                ws_out.cell(row=r, column=7).value = link
                
                web_data.append({
                    "id": int(float(num_val)),
                    "name": str(name_val).strip() if name_val else "",
                    "catalog": cat_str,
                    "unit": str(unit_val).strip() if unit_val else "",
                    "price": int(price) if price is not None else None,
                    "link": str(link).strip() if link else ""
                })
            except ValueError:
                pass
                
    wb_out.save(OUTPUT_EXCEL_PATH)
    log_message(f"Excel saved successfully to {OUTPUT_EXCEL_PATH}")
    
    # Save to data.json
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(web_data, f, ensure_ascii=False, indent=2)
    log_message(f"Saved data.json successfully to {JSON_OUTPUT_PATH}")
    
    # Save to data.js
    js_content = f"window.partsData = {json.dumps(web_data, ensure_ascii=False, indent=2)};"
    with open(JS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(js_content)
    log_message("Saved data.js successfully.")
    
    log_message("All tasks completed successfully!")

if __name__ == "__main__":
    main()
