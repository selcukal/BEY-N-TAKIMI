from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        question = request.form['question']
        return f"En iyi model seçildi ve cevaplandı: {question}"
    return '<form method="post"><input name="question" /><input type="submit" /></form>'

if __name__ == '__main__':
    app.run(debug=True)
