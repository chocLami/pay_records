from abc import ABC, abstractmethod
from collections import namedtuple
from csv import DictWriter, reader
from dataclasses import dataclass
from decimal import Decimal
from time import strftime
from typing import Dict, Generator, List

TaxBracket = namedtuple('TaxBracket', ['lower_bound', 'upper_bound', 'rates', 'fixed_amount'], defaults=(
    Decimal('0.0'), Decimal('0.0'), Decimal('0.0'), Decimal('0.0')))


class TaxCalculator:
    def __init__(self, tax_brackets):
        self._tax_brackets = tax_brackets

    def calculate_tax(self, income):
        for bracket in self._tax_brackets:
            if bracket.lower_bound <= income < bracket.upper_bound:
                return bracket.rates * income - bracket.fixed_amount
        raise ValueError(f"No suitable tax bracket for income: {income}")


@dataclass
class PayRecord(ABC):
    _id: int
    _hours: List[Decimal]
    _rates: List[Decimal]
    _tax_calculator: TaxCalculator

    @property
    def id(self) -> int:
        return self._id

    @property
    @abstractmethod
    def income(self) -> Decimal:
        return NotImplementedError

    @property
    def tax(self) -> Decimal:
        return self._tax_calculator.calculate_tax(self.income)

    @property
    def net(self) -> Decimal:
        return self.income - self.tax

    @abstractmethod
    def records_to_console(self) -> str:
        return NotImplementedError

    def add_hours(self, hours: List[Decimal]) -> None:
        if not all(isinstance(hour, Decimal) for hour in hours):
            raise TypeError("All hours must be of type Decimal.")
        self._hours.extend(hours)

    def add_rates(self, rates: List[Decimal]) -> None:
        if not all(isinstance(rate, Decimal) for rate in rates):
            raise TypeError("All rates must be of type Decimal.")
        self._rates.extend(rates)

    def _format_record(self, additional_info: str = ""):
        return (f"\nID: {self.id}"
                f"\nHours: {self._hours}"
                f"\nHourly Rate: {self._rates}"
                f"\nIncome: {self.income}"
                f"\nTotal Tax: {self.tax:.2f}"
                f"{additional_info}"
                f"\n{'_' * 35}")


@dataclass
class ResidentPayRecord(PayRecord):
    """ResidentPayRecord represents a pay record for a resident."""

    TAX_BRACKETS = [
        TaxBracket(0, 72, Decimal('0.19'), Decimal('0.19')),
        TaxBracket(72, 361, Decimal('0.2342'), Decimal('3.213')),
        TaxBracket(361, 932, Decimal('0.3477'), Decimal('44.2476')),
        TaxBracket(932, 1380, Decimal('0.345'), Decimal('41.7311')),
        TaxBracket(1380, 3111, Decimal('0.39'), Decimal('103.8657')),
        TaxBracket(3111, Decimal('infinity'), Decimal('0.47'), Decimal('352.788')),
    ]

    def __init__(self, _id, _hours, _rates):
        super().__init__(_id, _hours, _rates, TaxCalculator(self.TAX_BRACKETS))

    @property
    def income(self):
        return sum(hour * rate for hour, rate in zip(self._hours, self._rates))

    def records_to_console(self) -> str:
        return self._format_record()

    def __str__(self) -> str:
        return self.records_to_console()

@dataclass
class WorkingHolidayPayRecord(PayRecord):
    """WorkingHolidayPayRecord represents a pay record for an employee on a working holiday."""

    _visa: str
    _year_to_date: Decimal

    TAX_BRACKETS = [
        TaxBracket(0, 37000, Decimal('0.15')),
        TaxBracket(37000, 90000, Decimal('0.32')),
        TaxBracket(90000, 180000, Decimal('0.37')),
        TaxBracket(180000, Decimal('infinity'), Decimal('0.45')),
    ]

    def __init__(self, _id, _hours, _rates, _visa, _year_to_date):
        super().__init__(_id, _hours, _rates, TaxCalculator(self.TAX_BRACKETS))
        self._visa = _visa
        self._year_to_date = _year_to_date

    @property
    def income(self):
        return self._year_to_date + sum(hour * rate for hour, rate in zip(self._hours, self._rates))

    @property
    def year_to_date(self):
        return self._year_to_date

    def records_to_console(self) -> str:
        additional_info = f"\nVisa Type: {self._visa}\nYear to Date: {self._year_to_date}"
        return self._format_record(additional_info)

    def __str__(self) -> str:
        return self.records_to_console()


def import_pay_records(file_name: str) -> Generator[List[str], None, None]:
    MIN_COLUMN_VAL = 3
    try:
        with open(file_name, "r") as file:
            read_pay_record = reader(file)
            next(read_pay_record)
            for row in read_pay_record:
                if len(row) < MIN_COLUMN_VAL:
                    raise ValueError(f"A row does not contain {MIN_COLUMN_VAL} columns: {row}")
                # additional checks could be added later
                yield row
    except FileNotFoundError:
        print(f"File not found: {file_name}")
    except PermissionError:
        print(f"Permission denied when attempting to open file: {file_name}")


def create_pay_record(employee_id: int, hours: List[Decimal], rates: List[Decimal], visa: str = None, year_to_date: Decimal = None) -> PayRecord:
    if any(hour <= 0 for hour in hours):
        raise ValueError("Hours worked must be positive values")
    if any(rate <= 0 for rate in rates):
        raise ValueError("Rates must be positive values")
    # additional checks could be added later
    if visa:
        return WorkingHolidayPayRecord(employee_id, hours, rates, visa, year_to_date)
    else:
        return ResidentPayRecord(employee_id, hours, rates)


def export_to_csv(records: Dict[int, PayRecord], csvfile) -> None:
    header = ['id', 'income', 'tax', 'net', 'visa', 'yeartodate']
    writer = DictWriter(csvfile, fieldnames=header)

    writer.writeheader()
    for record in records.values():
        row = {
            'id': record.id,
            'income': record.income,
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
    output_records = fr"F:\Python Assessment Learning - Copy\pay_records\employee-payroll-output-{timestamp}-REFACTOR.csv"

    combined_records = {}

    for row in import_pay_records(pay_records):
        employee_id = int(row[0])
        hours = [Decimal(hour) for hour in row[1].split(",")]
        rates = [Decimal(rate) for rate in row[2].split(",")]
        try:
            visa = str(row[3]) if row[3] in ('417', '462') else None
            year_to_date = Decimal(row[4]) if row[4] else Decimal(0)
        except IndexError:
            visa = None
            year_to_date = None

        if employee_id not in combined_records:
            combined_records[employee_id] = create_pay_record(
                employee_id, hours, rates, visa, year_to_date)
            #print(f"Created new pay record for employee {employee_id}")

        else:
            combined_records[employee_id].add_hours(hours)
            combined_records[employee_id].add_rates(rates)  # same as above
            #print(f"Updated pay record for employee {employee_id}")

    with open(output_records, 'w', newline='') as csvfile:
        export_to_csv(combined_records, csvfile)

    for record in combined_records.values():
        print(record)


if __name__ == "__main__":
    main()
