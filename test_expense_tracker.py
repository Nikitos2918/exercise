import unittest
from datetime import date

from expense_tracker import (
    Expense,
    expenses_from_jsonable,
    parse_amount,
    parse_date,
    sum_for_period,
)


class TestValidation(unittest.TestCase):
    def test_parse_amount_positive(self):
        self.assertAlmostEqual(parse_amount("10"), 10.0)
        self.assertAlmostEqual(parse_amount("10.50"), 10.5)
        self.assertAlmostEqual(parse_amount("10,50"), 10.5)

    def test_parse_amount_negative_and_zero(self):
        with self.assertRaises(ValueError):
            parse_amount("0")
        with self.assertRaises(ValueError):
            parse_amount("-1")

    def test_parse_amount_not_number(self):
        with self.assertRaises(ValueError):
            parse_amount("abc")
        with self.assertRaises(ValueError):
            parse_amount("")

    def test_parse_date_positive(self):
        self.assertEqual(parse_date("2026-04-30"), date(2026, 4, 30))

    def test_parse_date_invalid(self):
        with self.assertRaises(ValueError):
            parse_date("30-04-2026")
        with self.assertRaises(ValueError):
            parse_date("2026/04/30")
        with self.assertRaises(ValueError):
            parse_date("")


class TestJson(unittest.TestCase):
    def test_expenses_from_jsonable_ok(self):
        data = [
            {"amount": 100, "category": "еда", "date": "2026-04-01"},
            {"amount": "50.5", "category": "транспорт", "date": "2026-04-02"},
        ]
        expenses = expenses_from_jsonable(data)
        self.assertEqual(len(expenses), 2)
        self.assertEqual(expenses[0].category, "еда")
        self.assertEqual(expenses[1].amount, 50.5)

    def test_expenses_from_jsonable_invalid_format(self):
        with self.assertRaises(ValueError):
            expenses_from_jsonable({"amount": 1})
        with self.assertRaises(ValueError):
            expenses_from_jsonable(["bad"])

    def test_expenses_from_jsonable_invalid_item(self):
        with self.assertRaises(ValueError):
            expenses_from_jsonable([{ "amount": -1, "category": "еда", "date": "2026-04-01" }])


class TestSum(unittest.TestCase):
    def test_sum_for_period_all(self):
        expenses = [
            Expense(amount=10.0, category="еда", date="2026-04-01"),
            Expense(amount=20.0, category="транспорт", date="2026-04-10"),
            Expense(amount=30.0, category="еда", date="2026-05-01"),
        ]
        total = sum_for_period(expenses, date(2026, 4, 1), date(2026, 4, 30))
        self.assertAlmostEqual(total, 30.0)

    def test_sum_for_period_category(self):
        expenses = [
            Expense(amount=10.0, category="еда", date="2026-04-01"),
            Expense(amount=20.0, category="транспорт", date="2026-04-10"),
            Expense(amount=15.0, category="еда", date="2026-04-10"),
        ]
        total = sum_for_period(expenses, date(2026, 4, 1), date(2026, 4, 30), "еда")
        self.assertAlmostEqual(total, 25.0)

    def test_sum_for_period_boundaries_inclusive(self):
        expenses = [
            Expense(amount=10.0, category="еда", date="2026-04-01"),
            Expense(amount=20.0, category="еда", date="2026-04-30"),
        ]
        total = sum_for_period(expenses, date(2026, 4, 1), date(2026, 4, 30), "еда")
        self.assertAlmostEqual(total, 30.0)


if __name__ == "__main__":
    unittest.main()

