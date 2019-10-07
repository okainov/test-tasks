import csv


def get_iata_timezone(iata_code: str) -> str:
    """
    Function used to determine airport's timezone based on the dataset from https://raw.githubusercontent.com/hroptatyr/dateutils/tzmaps/iata.tzmap
    See https://stackoverflow.com/a/21860150/1657819
    :param iata_code: 3-letter airport IATA code
    :return: string representation of the timezone in the given airport or empty string if nothing found
    """
    IATA_INDEX = 0
    TZ_INDEX = 1

    # TODO: workarounds for the missing codes, needs to be upstreamed
    if iata_code == 'XNB':
        return 'Asia/Qatar'

    # TODO: implement some caching to do not re-read the file every time
    with open('iata.tzmap', 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter='\t')
        for row in reader:
            if row[IATA_INDEX] == iata_code:
                return row[TZ_INDEX]
    return ''
