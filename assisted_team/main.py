import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS

from core import TravelParser

app = Flask(__name__)
CORS(app)


@app.route('/api/flights')
def flights():
    # TODO: actually use the parameters :)
    source = request.args.get('source', 'DXB')
    destination = request.args.get('destination', 'BKK')

    parser = TravelParser()
    result = []
    for travel in parser.parse_travels():
        result.append(travel.serialize())
    return jsonify(result)


@app.route('/api/top')
def top_flights():
    # TODO: add currency_output parameter
    criteria = request.args.get('criteria', 'price')
    sort = request.args.get('sort', 'asc')

    if criteria == 'price':
        # TODO: add amount of persons as API parameter
        criteria_getter = lambda x: x.calculate_price()
    elif criteria == 'duration':
        criteria_getter = lambda x: x.get_total_duration()
    else:
        criteria_getter = lambda x: x.get_suitability_index()

    if sort == 'desc':
        criteria_comparer = lambda x, y: x is None or x > y
    else:
        criteria_comparer = lambda x, y: x is None or x < y

    best_travels = []
    best_value = None
    parser = TravelParser()
    for travel in parser.parse_travels():
        criteria_value = criteria_getter(travel)
        if criteria_value == best_value:
            best_travels.append(travel.serialize())
        elif criteria_comparer(best_value, criteria_value):
            best_travels = [travel.serialize()]
            best_value = criteria_value
    if isinstance(best_value, datetime.timedelta):
        best_value = str(best_value)
    return jsonify({'travels': best_travels, 'value': best_value})


if __name__ == '__main__':
    app.run(port=8080, host='0.0.0.0')
