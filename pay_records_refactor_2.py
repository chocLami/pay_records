from abc import ABC, abstractmethod
from collections import namedtuple
from csv import DictWriter, reader
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Generator
from time import strftime


#How to implement TaxBracket helper function
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
        pass

    @property
    def tax(self) -> Decimal:
        return self._tax_calculator.calculate_tax(self.income)

    @property
    def net(self) -> Decimal:
        return self.income - self.tax

    @abstractmethod
    def records_to_console(self) -> str:
        pass

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
    TAX_BRACKETS = [
        TaxBracket(0, 72, Decimal('0.19'), Decimal('0.19')),
        TaxBracket(72, 361, Decimal('0.2342'), Decimal('3.213')),
        TaxBracket(361, 932, Decimal('0.3477'), Decimal('44.2476')),
        TaxBracket(932, 1380, Decimal('0.345'), Decimal('41.7311')),
        TaxBracket(1380, 3111, Decimal('0.39'), Decimal('103.8657')),
        TaxBracket(3111, Decimal('infinity'),
                   Decimal('0.47'), Decimal('352.788')),
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


class PayRecordIO(ABC):
    @abstractmethod
    def read_pay_records(self, file_name: str) -> Generator[List[str], None, None]:
        pass

    @abstractmethod
    def write_pay_records(self, records: Dict[int, PayRecord], file_name: str) -> None:
        pass


class CsvPayRecordIO(PayRecordIO):
    MIN_COLUMN_VAL = 3

    def read_pay_records(self, file_name: str) -> Generator[List[str], None, None]:
        try:
            with open(file_name, "r") as file:
                read_pay_record = reader(file)
                next(read_pay_record)
                for row in read_pay_record:
                    if len(row) < self.MIN_COLUMN_VAL:
                        raise ValueError(
                            f"A row does not contain {self.MIN_COLUMN_VAL} columns: {row}")
                    yield row
        except FileNotFoundError:
            print(f"File not found: {file_name}")
        except PermissionError:
            print(
                f"Permission denied when attempting to open file: {file_name}")

    def write_pay_records(self, records: Dict[int, PayRecord], file_name: str) -> None:
        header = ['id', 'income', 'tax', 'net', 'visa', 'yeartodate']
        with open(file_name, 'w', newline='') as csvfile:
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


class PayRecordFactory(ABC):
    @abstractmethod
    def create(self, employee_id: int, hours: List[Decimal], rates: List[Decimal], visa: str = None,
               year_to_date: Decimal = None) -> PayRecord:
        pass


class PayRecordFactoryImpl(PayRecordFactory):
    def create(self, employee_id: int, hours: List[Decimal], rates: List[Decimal], visa: str = None, year_to_date: str = None) -> PayRecord:
        if visa and year_to_date:
            return WorkingHolidayPayRecord(employee_id, hours, rates, visa, Decimal(year_to_date))
        else:
            return ResidentPayRecord(employee_id, hours, rates)


class PaySlipGenerator:
    def __init__(self, pay_record_factory: PayRecordFactory, pay_record_io: PayRecordIO):
        self._factory = pay_record_factory
        self._io = pay_record_io

    def generate_payslips(self, input_file: str, output_file: str) -> None:
        records = self._read_records(input_file)
        self._io.write_pay_records(records, output_file)
        for record in records.values():
            print(record)

    def _read_records(self, input_file: str) -> Dict[int, PayRecord]:
        records = {}
        for row in self._io.read_pay_records(input_file):
            employee_id, hours, rates, *rest = row
            employee_id = int(employee_id)
            hours = [Decimal(hour) for hour in hours.split(',')]
            rates = [Decimal(rate) for rate in rates.split(',')]
            if employee_id not in records:
                records[employee_id] = self._factory.create(
                    employee_id, hours, rates, *rest)
            else:
                records[employee_id].add_hours(hours)
                records[employee_id].add_rates(rates)
        return records


def main():
    payslip_generator = PaySlipGenerator(PayRecordFactoryImpl(), CsvPayRecordIO())
    payslip_generator.generate_payslips('employee-payroll-data.csv', 'output.csv')


if __name__ == "__main__":
    main()
