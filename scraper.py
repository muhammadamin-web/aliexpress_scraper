import http.client
import json
import csv
import re
import os
import unicodedata
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), "scraper_log.txt")

# API Configuration (multiple keys)
API_KEYS = [
    "99364c9f8emsh9636bdd52276833p162431jsnf4861c37c5aa",
    "755e78b3d4msh595239a3a89c04ep1b017bjsn4d058800f2fc",
    "698523c63fmsh12400d3bfa893d2p19f7a7jsnf76142583d37",
    "Odcf3a2711mshf885b7b20318876p1b245djsn14a481e647e8",
    "4ed2492403msh322e6e65e324dbdp14f6f9jsn6d9d821f1cdO",
    "476ed7d4f1msh2b61ca169bd667fp19470fjsnfb3c384d8ea5",
    "a5080fb6damsh64e4bfOd62ce9d7p1dc7c8jsnca8753fbfb2d",
    "0dcf3a2711mshf885b7b20318876p1b245djsn14a481e647e8",
    "4ed2492403msh322e6e65e324dbdp14f6f9jsn6d9d821f1cd0",
    "a5080fb6damsh64e4bf0d62ce9d7p1dc7c8jsnca8753fbfb2d"
    # Add more keys as needed
]
current_key_index = 0

API_HOST = "aliexpress-datahub.p.rapidapi.com"

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as logf:
            logf.write(line + "\n")
    except Exception as e:
        print(f"Log fayliga yozishda xatolik: {e}")

def create_slug(text):
    text = text.strip().lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-{2,}', '-', text)
    return text.strip('-')

def make_api_request(endpoint, item_id=None):
    global current_key_index
    max_attempts = len(API_KEYS) * 2
    attempts = 0

    while attempts < max_attempts:
        key = API_KEYS[current_key_index]
        headers = {
            'x-rapidapi-key': key,
            'x-rapidapi-host': API_HOST
        }
        try:
            conn = http.client.HTTPSConnection(API_HOST)
            url = f"{endpoint}?itemId={item_id}" if item_id else endpoint
            conn.request("GET", url, headers=headers)
            res = conn.getresponse()

            if res.status == 429:
                log_message(f"🔁 [429] Limit oshdi: Key #{current_key_index + 1}")
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                attempts += 1
                continue

            if res.status >= 400:
                raise Exception(f"❌ HTTP error: {res.status} {res.reason}")

            result = json.loads(res.read().decode("utf-8"))
            log_message(f"✅ API success with key #{current_key_index + 1}")
            return result

        except Exception as e:
            log_message(f"⚠️ API so'rovida xatolik: {str(e)}")
            current_key_index = (current_key_index + 1) % len(API_KEYS)
            attempts += 1

    raise Exception("❌ Barcha API keylar ikki martadan sinab chiqildi, ammo hech biri ishlamadi.")

def get_product_reviews(item_id):
    try:
        data = make_api_request("/item_review", item_id)
        if not data:
            return {'reviews': [], 'average_rating': ''}

        reviews = []
        for review in data.get('result', {}).get('resultList', []):
            review_data = review.get('review', {})
            buyer_data = review.get('buyer', {})
            reviews.append({
                'user_name': buyer_data.get('buyerTitle', ''),
                'region': buyer_data.get('buyerCountry', ''),
                'description': review_data.get('translation', {}).get('reviewContent', ''),
                'date': review_data.get('reviewDate', ''),
                'stars': review_data.get('reviewStarts', '')
            })

        average_rating = data.get('result', {}).get('base', {}).get('reviewStats', {}).get('evarageStar', '')
        return {
            'reviews': reviews,
            'average_rating': str(average_rating) if average_rating else ''
        }

    except Exception as e:
        log_message(f"Reytinglarni olishda xatolik: {str(e)}")
        return {'reviews': [], 'average_rating': ''}

def get_combined_product_reviews(item_id):
    try:
        data = make_api_request("/item_review_2", item_id)
        if not data:
            return []

        reviews = []
        for review in data.get('result', {}).get('resultList', []):
            review_data = review.get('review', {})
            buyer_data = review.get('buyer', {})
            reviews.append({
                'user_name': buyer_data.get('buyerTitle', ''),
                'region': buyer_data.get('buyerCountry', ''),
                'description': review_data.get('translation', {}).get('reviewContent', ''),
                'date': review_data.get('reviewDate', ''),
                'stars': review_data.get('reviewStarts', '')
            })

        return reviews

    except Exception as e:
        log_message(f"Sharhlarni olishda xatolik (/item_review_2): {str(e)}")
        return []

def get_product_description(item_id):
    try:
        data = make_api_request("/item_desc", item_id)
        if not data:
            return {'short_description': ''}
        description_text = data.get('result', {}).get('item', {}).get('description', {}).get('text', [])
        full_description = "\n".join(description_text) if description_text else ''
        return {'short_description': full_description[:1000]}
    except Exception as e:
        log_message(f"Tavsifni olishda xatolik: {str(e)}")
        return {'short_description': ''}

def get_product_data(item_id):
    data = make_api_request("/item_detail_2", item_id)
    if not data:
        log_message("Mahsulot ma'lumotlarini olishda xatolik")
        return None
    return data

def parse_product_data(data, average_rating=''):
    try:
        item = data.get('result', {}).get('item', {})
        images = []
        for img in item.get('images', []):
            if not img.startswith(('http://', 'https://')):
                img = 'https:' + img if img.startswith('//') else 'https://' + img.lstrip('/')
            images.append(img)
        price = item.get('sku', {}).get('def', {}).get('price', '')
        if isinstance(price, (int, float)):
            min_price = str(price)
        else:
            price_text = str(price)
            min_price = price_text.split('-')[0].strip() if price_text else ''
            min_price = ''.join(c for c in min_price if c.isdigit() or c == '.')
        category = ' > '.join(cat.get('title', '') for cat in item.get('breadcrumbs', []) if cat.get('title'))
        category_slug = create_slug(category)
        return {
            'title': item.get('title', ''),
            'price': min_price,
            'images': images,
            'rating': average_rating,
            'category': category_slug
        }
    except Exception as e:
        log_message(f"Ma'lumotlarni tahlil qilishda xatolik: {str(e)}")
        return None

def save_to_csv(product, reviews, filename='aliexpress_products.csv'):
    try:
        images = product.get('images', [])
        image_columns = {
            'Product main image': images[0] if images else '',
            '#1 Additional image': images[1] if len(images) > 1 else '',
            '#2 Additional image': images[2] if len(images) > 2 else '',
            '#3 Additional image': images[3] if len(images) > 3 else ''
        }
        row_data = {
            'Product title': product.get('title', ''),
            'Product price': product.get('price', ''),
            'Short description': product.get('short_description', '')[:1000],
            'Rating': product.get('rating', ''),
            'Category': product.get('category', ''),
            **image_columns
        }
        for i, review in enumerate(reviews[:3], 1):
            row_data.update({
                f'#{i} Testimonial user name': review.get('user_name', ''),
                f'#{i} Testimonial description': review.get('description', ''),
                f'#{i} Testimonial Date': review.get('date', ''),
                f'#{i} Testimonial Stars': review.get('stars', '')
            })
        file_exists = os.path.isfile(filename)
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=row_data.keys(), quoting=csv.QUOTE_ALL, delimiter=',')
            if not file_exists:
                writer.writeheader()
            writer.writerow(row_data)
        log_message(f"✅ Mahsulot ma'lumotlari {filename} fayliga saqlandi")
    except Exception as e:
        log_message(f"CSV fayliga saqlashda xatolik: {str(e)}")

def save_reviews_to_csv(product_slug, product_reviews, filename='reviews.csv'):
    try:
        rows = []
        for i, review in enumerate(product_reviews, 1):
            user_name = review.get('user_name', '')
            review_slug = create_slug(user_name) + f"-{i}"
            rows.append({
                'Name': user_name,
                'Slug': review_slug,
                'Date': review.get('date', ''),
                'Region': review.get('region', ''),
                'Desctription': review.get('description', ''),
                'Stars': review.get('stars', ''),
                'Product': product_slug
            })
        file_exists = os.path.isfile(filename)
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f,
                fieldnames=['Name', 'Slug', 'Date', 'Region', 'Desctription', 'Stars', 'Product'],
                quoting=csv.QUOTE_ALL, delimiter=',')
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows)
        log_message(f"✅ Sharhlar '{filename}' fayliga saqlandi")
    except Exception as e:
        log_message(f"Sharhlarni saqlashda xatolik: {str(e)}")

def run_scraper(raw_input):
    item_ids = [item.strip() for item in raw_input.replace('\n', ',').split(',') if item.strip()]
    for item_id in item_ids:
        log_message(f"\n🔍 {item_id} ID bo‘yicha ma’lumotlar olinmoqda...")
        try:
            data = get_product_data(item_id)
            if not data:
                log_message(f"⚠️ {item_id} uchun ma’lumot topilmadi")
                continue

            average_data = get_product_reviews(item_id)
            reviews_2 = get_combined_product_reviews(item_id)
            all_reviews = average_data['reviews'] + reviews_2

            descriptions = get_product_description(item_id)
            product = parse_product_data(data, average_data.get('average_rating', ''))

            if product:
                product.update(descriptions)
                log_message(f"\n📦 Mahsulot: {product.get('title')}")
                log_message(f"💵 Narxi: {product.get('price')} USD")
                log_message(f"⭐ Reyting: {product.get('rating')}")
                log_message(f"📁 Kategoriya: {product.get('category')}")
                log_message(f"📝 Tavsif: {product.get('short_description', '')[:80]}...")
                log_message(f"💬 Sharhlar soni: {len(all_reviews)}")

                save_to_csv(product, all_reviews[:3])
                product_slug = create_slug(product.get('title', ''))
                save_reviews_to_csv(product_slug, all_reviews)

        except Exception as e:
            log_message(f"❌ {item_id} uchun xatolik: {str(e)}")
