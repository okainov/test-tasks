from flask import Flask, escape, request, jsonify
from flask_cors import CORS

from core import TravelParser

app = Flask(__name__)
CORS(app)


@app.route('/')
def hello():
    name = request.args.get("name", "World")
    return f'Hello, {escape(name)}!'


@app.route('/api/flights')
def flights():
    # TODO: actually use the parameters :)
    source = request.args.get("source", "DXB")
    destination = request.args.get("destination", "BKK")

    parser = TravelParser()
    result = []
    for travel in parser.parse_travels():
        result.append(travel.serialize())
    return jsonify(result)


if __name__ == "__main__":
    app.run(port=8080)
