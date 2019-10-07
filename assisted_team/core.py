import datetime
import xml.etree.ElementTree as ET
from typing import List, Generator

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

    def validate(self) -> bool:
        return all([x is not None for x in [self.source, self.destination,
                                            self.arrival_time, self.departure_time]])

    def __repr__(self):
        return f'{self.carrier_id}{self.flight_number} {self.source} ({self.departure_time}) -> {self.destination} ' \
            f'({self.arrival_time}) [{self.arrival_time - self.departure_time}]'

    def __str__(self):
        return self.__repr__()

    def serialize(self) -> dict:
        return {
            'source': self.source,
            'destination': self.destination,
            'departure_time': self.departure_time.isoformat(),
            'arrival_time': self.arrival_time.isoformat(),
            'carrier': self.carrier,
            'flight_number': self.flight_number,
        }


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

    def set_currency(self, currency: str):
        self.price_currency = currency

    def get_currency(self) -> str:
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
        HOURS_IN_DAY = 60 * 60
        duration = self.get_total_duration()

        total_hours = duration.days * HOURS_IN_DAY + duration.seconds // SECONDS_IN_HOUR
        # Normalize prices to one currency so several different flights can be compared
        total_price = self.calculate_price(currency=Travel.DEFAULT_CURRENCY)

        return total_hours * total_price

    def serialize(self) -> dict:
        return {
            'price_currency': self.price_currency,
            'price_information': [{'type': fare_type, 'price': price} for fare_type, price in
                                  self.total_prices.items()],
            'flights': [f.serialize() for f in self.flights],
        }


class TravelParser:
    def __init__(self, filename: str = 'RS_ViaOW.xml'):
        self.filename = filename

    def parse_travels(self) -> Generator[Travel, None, None]:
        current_flight = Flight()
        current_travel = Travel()
        # TODO: validation of malformed/unrecognized format XMLs
        # use "iterparse" to be able to parse XMLs which are bigger than memory. Same reason for using generators
        for event, data in ET.iterparse(self.filename):
            if data.tag == 'Source':
                current_flight.set_source(data.text)
            elif data.tag == 'Destination':
                current_flight.set_destination(data.text)

            elif data.tag == 'Carrier':
                current_flight.set_carrier(data.text)
                current_flight.set_carrier_id(data.attrib['id'])
            elif data.tag == 'FlightNumber':
                current_flight.set_flight_number(data.text)

            # TODO: check for DST based on the actual datetime
            # TODO: we're relying on the order of XML fields here, i.e. "Source" and "Destination" have to go before
            #  datetime data, or Pricing data should come after Flights data
            elif data.tag == 'DepartureTimeStamp':
                local_departure_time = dateutil.parser.parse(data.text)
                current_flight.set_departure_time(
                    pytz.timezone(iata_timezone.get_iata_timezone(current_flight.get_source())).localize(
                        local_departure_time))
            elif data.tag == 'ArrivalTimeStamp':
                local_arrival_time = dateutil.parser.parse(data.text)
                current_flight.set_arrival_time(pytz.timezone(
                    iata_timezone.get_iata_timezone(current_flight.get_destination())).localize(local_arrival_time))

            elif data.tag == 'Flight':
                # Make sure flight is fully created at this point
                # TODO: implement proper validation
                assert current_flight.validate()
                current_travel.add_flight(current_flight)
                current_flight = Flight()

            elif data.tag == 'ServiceCharges':
                # TODO: Get use of other ChargeTypes?
                if data.attrib['ChargeType'] == 'TotalAmount':
                    current_travel.set_total_price(data.attrib['type'], float(data.text))
            elif data.tag == 'Pricing':
                current_travel.set_currency(data.attrib['currency'])
                yield current_travel
                current_travel = Travel()
