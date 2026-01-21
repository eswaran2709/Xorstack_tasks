from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def get_questions():
    
    url = "https://stackoverflow.com/questions/tagged/python"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        
        question_tags = soup.find_all('h3', class_='s-post-summary--content-title')
        
        questions_list = []
        for q in question_tags:
            title = q.find('a').get_text(strip=True)
            link = "https://stackoverflow.com" + q.find('a')['href']
            questions_list.append({"title": title, "link": link})
            
        return questions_list
    except Exception as e:
        return [{"title": f"Error: {str(e)}", "link": "#"}]

@app.route('/')
def home():
    
    data = get_questions()
    return render_template('scraper_ui.html', questions=data)

if __name__ == '__main__':
    app.run(debug=True)
