import json
import os
import tkinter as tk
from dataclasses import dataclass, asdict
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from tkinter import ttk, messagebox, filedialog


DATE_FMT = "%Y-%m-%d"


@dataclass(frozen=True)
class Expense:
    amount: float
    category: str
    date: str  # YYYY-MM-DD


def parse_amount(text: str) -> float:
    raw = (text or "").strip().replace(",", ".")
    if not raw:
        raise ValueError("Сумма не указана")

    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ValueError("Сумма должна быть числом")

    if value <= 0:
        raise ValueError("Сумма должна быть больше 0")

    return float(value)


def parse_date(text: str) -> date:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Дата не указана")
    try:
        return datetime.strptime(raw, DATE_FMT).date()
    except ValueError:
        raise ValueError("Дата должна быть в формате YYYY-MM-DD")


def normalize_category(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Категория не указана")
    return raw


def expenses_to_jsonable(expenses):
    return [asdict(e) for e in expenses]


def expenses_from_jsonable(data):
    if not isinstance(data, list):
        raise ValueError("Некорректный формат JSON: ожидается список")
    result = []
    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Некорректный элемент #{idx}: ожидается объект")
        amount = parse_amount(str(item.get("amount", "")))
        category = normalize_category(str(item.get("category", "")))
        d = parse_date(str(item.get("date", "")))
        result.append(Expense(amount=amount, category=category, date=d.strftime(DATE_FMT)))
    return result


def sum_for_period(expenses, start: date, end: date, category: str = "") -> float:
    total = 0.0
    category_norm = (category or "").strip()
    for e in expenses:
        d = parse_date(e.date)
        if d < start or d > end:
            continue
        if category_norm and e.category != category_norm:
            continue
        total += float(e.amount)
    return total


class ExpenseTrackerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Expense Tracker")
        self.expenses = []
        self.file_path = os.path.join(os.path.dirname(__file__), "expenses.json")

        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        input_frame = ttk.LabelFrame(main, text="Добавление расхода", padding=10)
        input_frame.grid(row=0, column=0, sticky="ew")
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="Сумма:").grid(row=0, column=0, sticky="w")
        self.amount_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.amount_var, width=20).grid(row=0, column=1, sticky="ew", padx=(8, 0))

        ttk.Label(input_frame, text="Категория:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.category_var = tk.StringVar()
        self.category_cb = ttk.Combobox(
            input_frame,
            textvariable=self.category_var,
            values=["еда", "транспорт", "развлечения", "прочее"],
            state="normal",
        )
        self.category_cb.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))

        ttk.Label(input_frame, text="Дата (YYYY-MM-DD):").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.date_var = tk.StringVar(value=date.today().strftime(DATE_FMT))
        ttk.Entry(input_frame, textvariable=self.date_var, width=20).grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))

        btns = ttk.Frame(input_frame)
        btns.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        btns.columnconfigure(0, weight=1)
        ttk.Button(btns, text="Добавить расход", command=self.add_expense).grid(row=0, column=0, sticky="w")
        ttk.Button(btns, text="Загрузить JSON", command=self.load_json_dialog).grid(row=0, column=1, padx=(10, 0))
        ttk.Button(btns, text="Сохранить JSON", command=self.save_json_dialog).grid(row=0, column=2, padx=(10, 0))

        table_frame = ttk.LabelFrame(main, text="Расходы", padding=10)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        main.rowconfigure(1, weight=1)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_frame, columns=("amount", "category", "date"), show="headings", height=10)
        self.tree.heading("amount", text="Сумма")
        self.tree.heading("category", text="Категория")
        self.tree.heading("date", text="Дата")
        self.tree.column("amount", width=120, anchor="e")
        self.tree.column("category", width=200, anchor="w")
        self.tree.column("date", width=130, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        filter_frame = ttk.LabelFrame(main, text="Фильтр / сумма за период", padding=10)
        filter_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for c in range(1, 6):
            filter_frame.columnconfigure(c, weight=1)

        ttk.Label(filter_frame, text="Категория:").grid(row=0, column=0, sticky="w")
        self.filter_category_var = tk.StringVar()
        self.filter_category_cb = ttk.Combobox(filter_frame, textvariable=self.filter_category_var, state="normal")
        self.filter_category_cb.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        ttk.Label(filter_frame, text="С:").grid(row=0, column=2, sticky="e", padx=(10, 0))
        self.start_date_var = tk.StringVar(value=date.today().replace(day=1).strftime(DATE_FMT))
        ttk.Entry(filter_frame, textvariable=self.start_date_var, width=12).grid(row=0, column=3, sticky="ew", padx=(8, 0))

        ttk.Label(filter_frame, text="По:").grid(row=0, column=4, sticky="e", padx=(10, 0))
        self.end_date_var = tk.StringVar(value=date.today().strftime(DATE_FMT))
        ttk.Entry(filter_frame, textvariable=self.end_date_var, width=12).grid(row=0, column=5, sticky="ew", padx=(8, 0))

        action_row = ttk.Frame(filter_frame)
        action_row.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(10, 0))
        ttk.Button(action_row, text="Применить фильтр", command=self.apply_filter).grid(row=0, column=0, sticky="w")
        ttk.Button(action_row, text="Сбросить", command=self.reset_filter).grid(row=0, column=1, padx=(10, 0))
        ttk.Button(action_row, text="Посчитать сумму", command=self.calculate_sum).grid(row=0, column=2, padx=(10, 0))

        self.total_var = tk.StringVar(value="Итого: 0.00")
        ttk.Label(action_row, textvariable=self.total_var).grid(row=0, column=3, padx=(12, 0))

        self._update_category_filters()

    def _update_category_filters(self):
        cats = sorted({e.category for e in self.expenses})
        base = ["", "еда", "транспорт", "развлечения", "прочее"]
        values = []
        for v in base + cats:
            if v not in values:
                values.append(v)
        self.filter_category_cb["values"] = values

    def _refresh_table(self, rows=None):
        for i in self.tree.get_children():
            self.tree.delete(i)
        data = rows if rows is not None else self.expenses
        for e in data:
            self.tree.insert("", "end", values=(f"{e.amount:.2f}", e.category, e.date))

    def add_expense(self):
        try:
            amount = parse_amount(self.amount_var.get())
            category = normalize_category(self.category_var.get())
            d = parse_date(self.date_var.get())
        except ValueError as ex:
            messagebox.showerror("Ошибка ввода", str(ex))
            return

        self.expenses.append(Expense(amount=amount, category=category, date=d.strftime(DATE_FMT)))
        self.amount_var.set("")
        self.category_var.set("")
        self.date_var.set(date.today().strftime(DATE_FMT))
        self._update_category_filters()
        self._refresh_table()

    def _get_filter(self):
        cat = (self.filter_category_var.get() or "").strip()
        start = parse_date(self.start_date_var.get())
        end = parse_date(self.end_date_var.get())
        if start > end:
            raise ValueError("Дата 'С' не может быть позже даты 'По'")
        return cat, start, end

    def apply_filter(self):
        try:
            cat, start, end = self._get_filter()
        except ValueError as ex:
            messagebox.showerror("Ошибка фильтра", str(ex))
            return

        rows = []
        for e in self.expenses:
            d = parse_date(e.date)
            if d < start or d > end:
                continue
            if cat and e.category != cat:
                continue
            rows.append(e)
        self._refresh_table(rows)

    def reset_filter(self):
        self.filter_category_var.set("")
        self.start_date_var.set(date.today().replace(day=1).strftime(DATE_FMT))
        self.end_date_var.set(date.today().strftime(DATE_FMT))
        self.total_var.set("Итого: 0.00")
        self._refresh_table()

    def calculate_sum(self):
        try:
            cat, start, end = self._get_filter()
        except ValueError as ex:
            messagebox.showerror("Ошибка периода", str(ex))
            return

        total = sum_for_period(self.expenses, start, end, cat)
        self.total_var.set(f"Итого: {total:.2f}")

    def load_json_dialog(self):
        path = filedialog.askopenfilename(
            title="Загрузить JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.path.dirname(self.file_path),
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.expenses = expenses_from_jsonable(data)
            self.file_path = path
            self._update_category_filters()
            self.reset_filter()
        except Exception as ex:
            messagebox.showerror("Ошибка загрузки", str(ex))

    def save_json_dialog(self):
        path = filedialog.asksaveasfilename(
            title="Сохранить JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=os.path.basename(self.file_path),
            initialdir=os.path.dirname(self.file_path),
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(expenses_to_jsonable(self.expenses), f, ensure_ascii=False, indent=2)
            self.file_path = path
            messagebox.showinfo("Сохранено", f"Данные сохранены в {os.path.basename(path)}")
        except Exception as ex:
            messagebox.showerror("Ошибка сохранения", str(ex))


def main():
    root = tk.Tk()
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    app = ExpenseTrackerApp(root)
    root.minsize(760, 520)
    root.mainloop()


if __name__ == "__main__":
    main()

