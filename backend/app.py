from flask import Flask, request
from classification_service import classify

app = Flask(__name__)

@app.route("/classify", methods=["POST"])
def classify():
    query = request.json["query"]

    return classify(query)


app.run(port=5000)
