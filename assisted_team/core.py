import datetime
import xml.etree.ElementTree as ET
from typing import List

import dateutil.parser
import pytz
from currency_converter import CurrencyConverter

import iata_timezone


class Flight:
    arrival_time: [datetime.datetime, None]
    departure_time: [datetime.datetime, None]

    def __init__(self):
        self.source = None
        self.destination = None
        self.arrival_time = None
        self.departure_time = None
        self.carrier = None
        self.carrier_id = None
        self.flight_number = None

    def get_destination(self):
        return self.destination

    def get_source(self) -> str:
        return self.source

    def set_source(self, source: str):
        self.source = source

    def set_arrival_time(self, arrival_time: datetime.datetime):
        self.arrival_time = arrival_time

    def get_arrival_time(self) -> datetime.datetime:
        return self.arrival_time

    def set_departure_time(self, departure_time: datetime.datetime):
        self.departure_time = departure_time

    def get_departure_time(self) -> datetime.datetime:
        return self.departure_time

    def set_destination(self, destination: str):
        self.destination = destination

    def set_carrier(self, carrier: str):
        self.carrier = carrier

    def set_carrier_id(self, carrier_id: str):
        self.carrier_id = carrier_id

    def set_flight_number(self, flight_number: str):
        self.flight_number = flight_number

    def get_duration(self) -> datetime.timedelta:
        return self.get_arrival_time() - self.get_departure_time()

    def validate(self):
        return all([x is not None for x in [self.source, self.destination,
                                            self.arrival_time, self.departure_time]])

    def __repr__(self):
        return f'{self.carrier_id}{self.flight_number} {self.source} ({self.departure_time}) -> {self.destination} ' \
            f'({self.arrival_time}) [{self.arrival_time - self.departure_time}]'

    def __str__(self):
        return self.__repr__()


class Travel:
    DEFAULT_CURRENCY = 'SGD'

    ADULT_TYPE = 'SingleAdult'
    CHILD_TYPE = 'SingleChild'
    INFANT_TYPE = 'SingleInfant'
    VALID_TYPES = [ADULT_TYPE, CHILD_TYPE, INFANT_TYPE]

    # TODO: split to itineraries
    flights: List[Flight]

    def __init__(self):
        self.flights = []
        self.price_currency = None
        self.total_prices = {}

    def set_currency(self, currency):
        self.price_currency = currency

    def get_currency(self):
        return self.price_currency

    def set_total_price(self, fare_type: str, total_price: float):
        self.total_prices[fare_type] = total_price

    def add_flight(self, flight: Flight):
        self.flights.append(flight)

    def __repr__(self):
        return f'{self.price_currency} {self.total_prices} \n\t' + '\n\t'.join(map(str, self.flights))

    def calculate_price(self, people=None, currency='') -> float:
        """
        Returns total prices of this travel for the given amount of people.
        :param people: dictionary with keys from VALID_TYPES list and values equal to the number of persons of the given
            type
        :param currency: 3-letter code of the currency, defaults to current Travel currency
        :return: amount of money in the given currency
        """
        if people is None:
            people = {Travel.ADULT_TYPE: 1}
        if not currency:
            currency = self.get_currency()
        total_in_travel_currency = 0

        for fare_type, amount in people.items():
            total_in_travel_currency += amount * self.total_prices[fare_type]

        if currency == self.get_currency():
            return total_in_travel_currency
        else:
            c = CurrencyConverter()
            return c.convert(total_in_travel_currency, self.get_currency(), currency)

    def get_total_duration(self) -> datetime.timedelta:
        total_duration = datetime.timedelta()
        for flight in self.flights:
            total_duration += flight.get_arrival_time() - flight.get_departure_time()
        return total_duration

    def get_suitability_index(self) -> float:
        """
        Calculates some relative "suitability" index of the travel itinerary. Initial version just returns
        duration*price ratio (less is better)
        # TODO: can be improved by taking into account some of:
            - explicit amount of stops
            - airline
            - class
            - time (middle of the local night departure/arrival is not good)
            - luggage allowance (if known)
            - transfer duration
            - countries/cities for the stopover (big city is better for stopover than lowcost's village)
            - relative "slowness" of the flight, when knowing the airports we can compare duration against
                theoretical perfect flight speed&duration
            - ...and many others...

        :return: index how "good" the flight is. Less is better
        """
        SECONDS_IN_HOUR = 60 * 60
        duration = self.get_total_duration()

        total_hours = duration.days * 24 + duration.seconds // SECONDS_IN_HOUR
        # Normalize prices to one currency so several different flights can be compared
        total_price = self.calculate_price(currency=Travel.DEFAULT_CURRENCY)

        return total_hours * total_price


root = ET.parse('RS_ViaOW.xml').getroot()

# Use iterparse because size of XML can be bigger than memory

path = []

total = -1
min_index = 1e10
min_travel = None
current_flight = Flight()
current_travel = Travel()
for event, data in ET.iterparse('RS_ViaOW.xml', events=('start', 'end')):
    # for event, data in ET.iterparse('RS_Via-3.xml', events=('start', 'end')):
    if event == 'start':
        path.append(data.tag)
        continue

    if data.tag == 'Source':
        current_flight.set_source(data.text)
    if data.tag == 'Destination':
        current_flight.set_destination(data.text)

    if data.tag == 'Carrier':
        current_flight.set_carrier(data.text)
        current_flight.set_carrier_id(data.attrib['id'])
    if data.tag == 'FlightNumber':
        current_flight.set_flight_number(data.text)

    # TODO: check for DST based on the actual datetime
    # TODO: we're relying on the order of XML fields here, i.e. "Source" and "Destination" have to go before
    #  datetime data, or Pricing data should come after Flights data
    if data.tag == 'DepartureTimeStamp':
        local_departure_time = dateutil.parser.parse(data.text)
        current_flight.set_departure_time(
            pytz.timezone(iata_timezone.get_iata_timezone(current_flight.get_source())).localize(
                local_departure_time))
    if data.tag == 'ArrivalTimeStamp':
        local_arrival_time = dateutil.parser.parse(data.text)
        current_flight.set_arrival_time(pytz.timezone(
            iata_timezone.get_iata_timezone(current_flight.get_destination())).localize(local_arrival_time))

    if data.tag == 'Flight':
        assert current_flight.validate()
        current_travel.add_flight(current_flight)
        current_flight = Flight()

    if data.tag == 'ServiceCharges':
        # TODO: Get use of other ChargeTypes?
        if data.attrib['ChargeType'] == 'TotalAmount':
            current_travel.set_total_price(data.attrib['type'], float(data.text))
    if data.tag == 'Pricing':
        current_travel.set_currency(data.attrib['currency'])
        print(current_travel)
        index = current_travel.get_suitability_index()
        if index < min_index:
            min_travel = current_travel
            min_index = index
        print(index)
        current_travel = Travel()
        print('---------')
    # TODO: validation of malformed/unrecognized format XMLs
    path.pop()

print('Min travel is %s' % min_index)
print(min_travel)
# print(root)
# for elem in root.iter():
#     print(elem)
