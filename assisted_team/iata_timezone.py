import csv


def get_iata_timezone(iata_code: str):
    """
    Funciton used to determine airport's timezone based on the dataset from https://openflights.org/data.html
    :param iata_code: 3-letter airport IATA code
    :return:
    """
    IATA_INDEX = 4
    TZ_INDEX = 11

    with open('airports.dat', 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            if row[IATA_INDEX] == iata_code:
                return row[TZ_INDEX]
    return None
