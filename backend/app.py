from flask import Flask, request, jsonify
import pickle

app = Flask(__name__)

model = pickle.load(open("model_training/query_router.pkl", "rb"))

@app.route("/classify", methods=["POST"])
def classify():
    query = request.json["query"]

    prediction = model.predict([query])[0]
    prob = model.predict_proba([query]).max()

    return jsonify({
        "route": prediction,
        "confidence": float(prob)
    })

app.run(port=5000)