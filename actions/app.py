from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=['http://localhost:8000'])

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True)
    user_message = data['message']
    rasa_response = send_message_to_rasa(user_message)
    return jsonify(rasa_response)

def send_message_to_rasa(message):
    rasa_api_url = 'http://localhost:5005/webhooks/rest/webhook'
    response = requests.post(rasa_api_url, json={'message': message})
    rasa_response = response.json()
    return rasa_response

if __name__ == '__main__':
    app.run(port=5000)