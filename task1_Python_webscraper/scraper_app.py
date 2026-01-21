from flask import Flask, render_template, send_file
import requests
from bs4 import BeautifulSoup
import csv
import os

app = Flask(__name__)

# --- SCRAPING LOGIC ---
def scrape_stackoverflow():
    url = "https://stackoverflow.com/questions/tagged/python?tab=newest&pagesize=50"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        questions = soup.find_all('div', class_='s-post-summary')
        
        data_list = []
        for q in questions:
            title_link = q.find('h3', class_='s-post-summary--content-title').find('a')
            title = title_link.get_text(strip=True)
            full_link = "https://stackoverflow.com" + title_link['href']
            description = q.find('div', class_='s-post-summary--content-excerpt').get_text(strip=True)
            tags = [tag.get_text() for tag in q.find_all('a', class_='post-tag')]
            keywords = ", ".join(tags)

            data_list.append({
                "title": title,
                "description": description,
                "keywords": keywords,
                "link": full_link
            })
        
        # Save a local copy
        save_to_csv(data_list)
        return data_list
    except Exception as e:
        print(f"Scraping Error: {e}")
        return []

def save_to_csv(data):
    filename = "scraped_questions.csv"
    keys = ['title', 'description', 'keywords', 'link']
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(data)

# --- ROUTES ---

@app.route('/')
def home():
    data = scrape_stackoverflow()
    return render_template('scraper_ui.html', questions=data)

# NEW ROUTE: Download the CSV file
@app.route('/download')
def download_file():
    path = "scraped_questions.csv"
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "File not found!", 404

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)