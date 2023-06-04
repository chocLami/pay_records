from abc import ABC, abstractmethod
from collections import namedtuple
from csv import DictWriter, reader
from decimal import Decimal
from time import strftime
from typing import Dict, Generator, List

TaxBracket = namedtuple('TaxBracket', ['lower_bound', 'upper_bound', 'rates', 'fixed_amount'], defaults=(
    Decimal('0.0'), Decimal('0.0'), Decimal('0.0'), Decimal('0.0')))


class PayRecord(ABC):
    def __init__(self, id: int, hours: List[Decimal], rates: List[Decimal]) -> None:
        self._id = id
        self._hours = hours
        self._rates = rates

    @property
    def id(self) -> int:
        return self._id

    @property
    @abstractmethod
    def gross(self) -> Decimal:
        return NotImplementedError

    @property
    @abstractmethod
    def tax(self) -> Decimal:
        return NotImplementedError

    @property
    def net(self) -> Decimal:
        return (self.gross - self.tax)

    @abstractmethod
    def records_to_console(self) -> str:
        return NotImplementedError

    def add_hours(self, hours: List[Decimal]) -> None:
        self._hours.extend(hours)

    def add_rates(self, rates: List[Decimal]) -> None:
        self._rates.extend(rates)


class ResidentPayRecord(PayRecord):
    def __init__(self, id: int, hours: List[Decimal], rates: List[Decimal]) -> None:
        super().__init__(id, hours, rates)

    TAX_BRACKETS = [
        TaxBracket(0, 72, Decimal('0.19'), Decimal('0.19')),
        TaxBracket(72, 361, Decimal('0.2342'), Decimal('3.213')),
        TaxBracket(361, 932, Decimal('0.3477'), Decimal('44.2476')),
        TaxBracket(932, 1380, Decimal('0.345'), Decimal('41.7311')),
        TaxBracket(1380, 3111, Decimal('0.39'), Decimal('103.8657')),
        TaxBracket(3111, Decimal('infinity'),
                   Decimal('0.47'), Decimal('352.788')),
    ]

    @property
    def tax(self):
        for bracket in self.TAX_BRACKETS:
            if bracket.lower_bound <= self.gross < bracket.upper_bound:
                return bracket.rates * self.gross - bracket.fixed_amount

    @property
    def gross(self):
        return sum(hour * rate
                   for hour, rate
                   in zip(self._hours, self._rates))

    def records_to_console(self) -> str:
        return (f"\nResident ID: {self._id}"
                f"\nHours: {self._hours}"
                f"\nHourly Rate: {self._rates}"
                f"\nGross: {self.gross}"
                f"\nTotal Tax: {self.tax:.2f}"
                f"\n{'_' * 35}")

    def __str__(self) -> str:
        return (f"\nResident ID: {self._id}"
                f"\nHours: {self._hours}"
                f"\nHourly Rate: {self._rates}"
                f"\nGross: {self.gross}"
                f"\nTotal Tax: {self.tax:.2f}"
                f"\n{'_' * 35}")


class WorkingHolidayPayRecord(PayRecord):
    def __init__(self, id: int, hours: List[Decimal], rates: List[Decimal], visa: str, year_to_date: Decimal) -> None:
        super().__init__(id, hours, rates)
        self._visa = visa
        self._year_to_date = year_to_date

    TAX_BRACKETS = [
        TaxBracket(0, 37000, Decimal('0.15')),
        TaxBracket(37000, 90000, Decimal('0.32')),
        TaxBracket(90000, 180000, Decimal('0.37')),
        TaxBracket(180000, Decimal('infinity'), Decimal('0.45')),
    ]

    @property
    def year_to_date(self) -> Decimal:
        return self._year_to_date + self.gross

    @property
    def gross(self):
        return sum(hour * rate
                   for hour, rate
                   in zip(self._hours, self._rates))

    @property
    def tax(self):
        for bracket in self.TAX_BRACKETS:
            if bracket.lower_bound <= self.year_to_date < bracket.upper_bound:
                return bracket.rates * self.gross

    def records_to_console(self) -> str:
        return (f"\nHoliday ID: {self._id}"
                f"\nHours: {self._hours}"
                f"\nHourly Rate: {self._rates}"
                f"\nGross: {self.gross}"
                f"\nVisa Type: {self._visa}"
                f"\nYear to Date: {self._year_to_date}"
                f"\nTotal Tax: {self.tax:.2f}"
                f"\n{'_' * 35}")

    def __str__(self) -> str:
        return (f"\nHoliday ID: {self._id}"
                f"\nHours: {self._hours}"
                f"\nHourly Rate: {self._rates}"
                f"\nGross: {self.gross}"
                f"\nVisa Type: {self._visa}"
                f"\nYear to Date: {self._year_to_date}"
                f"\nTotal Tax: {self.tax:.2f}"
                f"\n{'_' * 35}")


def import_pay_records(file_name: str) -> Generator[List[str], None, None]:
    with open(file_name, "r") as file:
        read_pay_record = reader(file)
        next(read_pay_record)
        yield from read_pay_record


def create_pay_record(employee_id: int, hours: List[Decimal], rates: List[Decimal], visa: str, year_to_date: Decimal) -> PayRecord:
    if visa:
        return WorkingHolidayPayRecord(employee_id, hours, rates, visa, year_to_date)
    else:
        return ResidentPayRecord(employee_id, hours, rates)


def export_to_csv(records: Dict[int, PayRecord], csvfile) -> None:
    header = ['id', 'gross', 'tax', 'net', 'visa', 'yeartodate']
    writer = DictWriter(csvfile, fieldnames=header)

    writer.writeheader()
    for record in records.values():
        row = {
            'id': record.id,
            'gross': record.gross,
            'tax': record.tax,
            'net': record.net,
        }
        if isinstance(record, WorkingHolidayPayRecord):
            row['visa'] = record._visa
            row['yeartodate'] = record.year_to_date
        else:
            row['visa'] = ''
            row['yeartodate'] = ''

        writer.writerow(row)


def main():

    timestamp = strftime("%Y-%m-%d_%H_%M_%S")
    pay_records = fr"F:\Python Assessment Learning - Copy\pay_records\employee-payroll-data.csv"
    output_records = fr"F:\Python Assessment Learning - Copy\pay_records\employee-payroll-output-{timestamp}.csv"

    combined_records = {}

    for row in import_pay_records(pay_records):
        employee_id = int(row[0])
        hours = [Decimal(hour) for hour in row[1].split(",")]
        rates = [Decimal(rate) for rate in row[2].split(",")]
        visa = str(row[3])
        year_to_date = Decimal(row[4]) if row[4] else Decimal(0)

        if employee_id not in combined_records:
            combined_records[employee_id] = create_pay_record(
                employee_id, hours, rates, visa, year_to_date)
            print(f"Created new pay record for employee {employee_id}")

        else:
            # previously used list method .extend()
            combined_records[employee_id].add_hours(hours)
            combined_records[employee_id].add_rates(rates)  # same as above
            print(f"Updated pay record for employee {employee_id}")

    with open(output_records, 'w', newline='') as csvfile:
        export_to_csv(combined_records, csvfile)

    for record in combined_records.values():
        print(record)


if __name__ == "__main__":
    main()
