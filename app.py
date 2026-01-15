from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return 'Flask funziona!'

if __name__ == '__main__':
    app.run(debug=True)