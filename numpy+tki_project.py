"""
Personal Expense Analyzer  (Python + NumPy + Tkinter + Matplotlib)

Install:  pip install numpy matplotlib
Run:      python expense_analyzer.py

Data is auto-saved to expenses.csv next to this script.
"""

import csv
import os
from datetime import datetime

import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.csv")
DATE_FMT = "%d-%m-%Y"
CURRENCY = "৳"


def money(x):
    return f"{CURRENCY} {x:,.2f}"


# ======================================================================
# DATA LAYER  (all calculations use NumPy)
# ======================================================================
class ExpenseStore:
    def __init__(self):
        self.dates = []
        self.categories = []
        self.amounts = np.array([], dtype=float)

    def __len__(self):
        return len(self.amounts)

    # ---------- CRUD ----------
    @staticmethod
    def _clean(date, category, amount):
        datetime.strptime(date, DATE_FMT)           # raises ValueError if invalid
        category = category.strip().title()
        amount = float(amount)
        if not category:
            raise ValueError("Category cannot be empty.")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        return date, category, amount

    def add(self, date, category, amount):
        date, category, amount = self._clean(date, category, amount)
        self.dates.append(date)
        self.categories.append(category)
        self.amounts = np.append(self.amounts, amount)

    def update(self, i, date, category, amount):
        date, category, amount = self._clean(date, category, amount)
        self.dates[i], self.categories[i], self.amounts[i] = date, category, amount

    def delete(self, i):
        self.dates.pop(i)
        self.categories.pop(i)
        self.amounts = np.delete(self.amounts, i)

    # ---------- persistence ----------
    def save(self, path=DATA_FILE):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date", "category", "amount"])
            for d, c, a in zip(self.dates, self.categories, self.amounts):
                w.writerow([d, c, f"{a:.2f}"])

    def load(self, path=DATA_FILE, replace=True):
        if not os.path.exists(path):
            return 0
        if replace:
            self.__init__()
        count = 0
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    self.add(row["date"], row["category"], row["amount"])
                    count += 1
                except (ValueError, KeyError):
                    continue                        # skip bad rows
        return count

    # ---------- analytics ----------
    def stats(self, mask=None):
        """Summary statistics for all expenses, or for a boolean mask."""
        idx = np.arange(len(self)) if mask is None else np.flatnonzero(mask)
        if idx.size == 0:
            return None
        arr = self.amounts[idx]
        hi, lo = idx[np.argmax(arr)], idx[np.argmin(arr)]
        return {
            "total": arr.sum(), "avg": arr.mean(), "median": np.median(arr),
            "std": arr.std(), "count": arr.size,
            "max": arr.max(), "min": arr.min(), "hi_i": hi, "lo_i": lo,
        }

    def category_totals(self, mask=None):
        """Returns (categories, totals, counts) sorted by total, descending."""
        idx = np.arange(len(self)) if mask is None else np.flatnonzero(mask)
        if idx.size == 0:
            return np.array([]), np.array([]), np.array([])
        cats = np.array(self.categories)[idx]
        uniq, inv = np.unique(cats, return_inverse=True)
        totals = np.bincount(inv, weights=self.amounts[idx])
        counts = np.bincount(inv)
        order = np.argsort(totals)[::-1]
        return uniq[order], totals[order], counts[order]

    def month_keys(self):
        return np.array([d[3:] for d in self.dates])          # "MM-YYYY"

    def months(self):
        uniq = np.unique(self.month_keys()) if len(self) else []
        return sorted(uniq, key=lambda m: (m[3:], m[:2]))

    def monthly_totals(self):
        months = self.months()
        keys = self.month_keys()
        return months, np.array([self.amounts[keys == m].sum() for m in months])

    def month_mask(self, month):
        return self.month_keys() == month


# ======================================================================
# GUI
# ======================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Personal Expense Analyzer")
        self.geometry("1100x720")
        self.minsize(960, 640)
        self.store = ExpenseStore()
        self.store.load()
        self.selected = None                         # index of selected expense

        self._style()
        self._menu()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_dash = ttk.Frame(nb)
        self.tab_exp = ttk.Frame(nb)
        self.tab_cat = ttk.Frame(nb)
        self.tab_mon = ttk.Frame(nb)
        for tab, name in [(self.tab_dash, "  Dashboard  "), (self.tab_exp, "  Expenses  "),
                          (self.tab_cat, "  Category Analysis  "), (self.tab_mon, "  Monthly Analysis  ")]:
            nb.add(tab, text=name)

        self._build_dashboard()
        self._build_expenses()
        self._build_category()
        self._build_monthly()
        self._status = tk.StringVar()
        ttk.Label(self, textvariable=self._status, anchor="w", relief="sunken").pack(fill="x", side="bottom")
        self.refresh_all()

    # ---------- setup ----------
    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Card.TLabelframe", padding=10)
        s.configure("CardValue.TLabel", font=("Segoe UI", 15, "bold"), foreground="#1f4e79")
        s.configure("Treeview", rowheight=24)
        s.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _menu(self):
        m = tk.Menu(self)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Import CSV...", command=self.import_csv)
        f.add_command(label="Export CSV...", command=self.export_csv)
        f.add_separator()
        f.add_command(label="Exit", command=self.destroy)
        m.add_cascade(label="File", menu=f)
        self.config(menu=m)

    def _make_tree(self, parent, cols, widths, height=12):
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=height)
        for c, w in zip(cols, widths):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor="e" if c in ("Amount", "Total", "Count", "Share") else "w")
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return frame, tree

    def _make_chart(self, parent, w=5, h=3.4):
        fig = Figure(figsize=(w, h), dpi=100)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        return fig, canvas

    # ---------- Dashboard tab ----------
    def _build_dashboard(self):
        top = ttk.Frame(self.tab_dash)
        top.pack(fill="x", padx=10, pady=10)
        self.cards = {}
        for i, (key, title) in enumerate([("total", "Total Expense"), ("avg", "Average"),
                                          ("max", "Highest"), ("min", "Lowest"), ("count", "Transactions")]):
            box = ttk.LabelFrame(top, text=title, style="Card.TLabelframe")
            box.grid(row=0, column=i, padx=5, sticky="ew")
            top.columnconfigure(i, weight=1)
            var = tk.StringVar(value="-")
            ttk.Label(box, textvariable=var, style="CardValue.TLabel").pack()
            self.cards[key] = var
        self.dash_note = tk.StringVar()
        ttk.Label(self.tab_dash, textvariable=self.dash_note, foreground="#555").pack(anchor="w", padx=14)

        charts = ttk.Frame(self.tab_dash)
        charts.pack(fill="both", expand=True, padx=10, pady=5)
        left, right = ttk.Frame(charts), ttk.Frame(charts)
        left.pack(side="left", fill="both", expand=True)
        right.pack(side="left", fill="both", expand=True)
        self.pie_fig, self.pie_canvas = self._make_chart(left)
        self.bar_fig, self.bar_canvas = self._make_chart(right)

    def refresh_dashboard(self):
        st = self.store.stats()
        if st is None:
            for v in self.cards.values():
                v.set("-")
            self.dash_note.set("No expenses yet. Add one in the Expenses tab.")
        else:
            self.cards["total"].set(money(st["total"]))
            self.cards["avg"].set(money(st["avg"]))
            self.cards["max"].set(money(st["max"]))
            self.cards["min"].set(money(st["min"]))
            self.cards["count"].set(str(st["count"]))
            hi, lo = st["hi_i"], st["lo_i"]
            self.dash_note.set(
                f"Highest: {self.store.categories[hi]} on {self.store.dates[hi]}   |   "
                f"Lowest: {self.store.categories[lo]} on {self.store.dates[lo]}   |   "
                f"Median: {money(st['median'])}   |   Std dev: {money(st['std'])}")

        # pie: spending by category
        self.pie_fig.clear()
        ax = self.pie_fig.add_subplot(111)
        cats, totals, _ = self.store.category_totals()
        if cats.size:
            ax.pie(totals, labels=cats, autopct="%1.0f%%", startangle=90, textprops={"fontsize": 8})
        else:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_title("Spending by Category", fontsize=10)
        self.pie_canvas.draw_idle()

        # bar: monthly totals
        self.bar_fig.clear()
        ax = self.bar_fig.add_subplot(111)
        months, mt = self.store.monthly_totals()
        if len(months):
            ax.bar(months, mt, color="#2e75b6")
            ax.tick_params(axis="x", rotation=45, labelsize=8)
        else:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_title("Monthly Spending", fontsize=10)
        self.bar_fig.tight_layout()
        self.bar_canvas.draw_idle()

    # ---------- Expenses tab ----------
    def _build_expenses(self):
        form = ttk.LabelFrame(self.tab_exp, text="Expense Details", padding=10)
        form.pack(fill="x", padx=10, pady=8)
        self.v_date = tk.StringVar(value=datetime.now().strftime(DATE_FMT))
        self.v_cat = tk.StringVar()
        self.v_amt = tk.StringVar()
        ttk.Label(form, text="Date (DD-MM-YYYY)").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.v_date, width=16).grid(row=1, column=0, padx=(0, 10))
        ttk.Label(form, text="Category").grid(row=0, column=1, sticky="w")
        self.cb_cat = ttk.Combobox(form, textvariable=self.v_cat, width=22)
        self.cb_cat.grid(row=1, column=1, padx=(0, 10))
        ttk.Label(form, text="Amount").grid(row=0, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.v_amt, width=14).grid(row=1, column=2, padx=(0, 10))
        ttk.Button(form, text="Add", command=self.add_expense).grid(row=1, column=3, padx=3)
        ttk.Button(form, text="Update Selected", command=self.update_expense).grid(row=1, column=4, padx=3)
        ttk.Button(form, text="Delete Selected", command=self.delete_expense).grid(row=1, column=5, padx=3)
        ttk.Button(form, text="Clear", command=self.clear_form).grid(row=1, column=6, padx=3)

        flt = ttk.LabelFrame(self.tab_exp, text="Filter", padding=10)
        flt.pack(fill="x", padx=10)
        self.f_cat = tk.StringVar()
        self.f_min = tk.StringVar()
        ttk.Label(flt, text="Category contains").pack(side="left")
        ttk.Entry(flt, textvariable=self.f_cat, width=18).pack(side="left", padx=6)
        ttk.Label(flt, text="Amount above").pack(side="left", padx=(12, 0))
        ttk.Entry(flt, textvariable=self.f_min, width=12).pack(side="left", padx=6)
        ttk.Button(flt, text="Apply", command=self.refresh_table).pack(side="left", padx=3)
        ttk.Button(flt, text="Reset", command=self.reset_filter).pack(side="left", padx=3)
        self.filter_info = tk.StringVar()
        ttk.Label(flt, textvariable=self.filter_info, foreground="#555").pack(side="right")

        frame, self.tree = self._make_tree(self.tab_exp, ("Date", "Category", "Amount"), (160, 300, 160), height=16)
        frame.pack(fill="both", expand=True, padx=10, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def _filter_mask(self):
        n = len(self.store)
        mask = np.ones(n, dtype=bool)
        text = self.f_cat.get().strip().lower()
        if text:
            mask &= np.array([text in c.lower() for c in self.store.categories], dtype=bool)
        if self.f_min.get().strip():
            try:
                mask &= self.store.amounts > float(self.f_min.get())
            except ValueError:
                messagebox.showerror("Invalid filter", "Amount filter must be a number.")
        return mask

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        mask = self._filter_mask()
        for i in np.flatnonzero(mask):
            self.tree.insert("", "end", iid=str(i),
                             values=(self.store.dates[i], self.store.categories[i], f"{self.store.amounts[i]:,.2f}"))
        shown = int(mask.sum())
        self.filter_info.set(f"Showing {shown} of {len(self.store)} | Sum: {money(self.store.amounts[mask].sum())}")

    def reset_filter(self):
        self.f_cat.set("")
        self.f_min.set("")
        self.refresh_table()

    def on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        self.selected = int(sel[0])
        i = self.selected
        self.v_date.set(self.store.dates[i])
        self.v_cat.set(self.store.categories[i])
        self.v_amt.set(f"{self.store.amounts[i]:.2f}")

    def clear_form(self):
        self.selected = None
        self.v_date.set(datetime.now().strftime(DATE_FMT))
        self.v_cat.set("")
        self.v_amt.set("")
        self.tree.selection_remove(self.tree.selection())

    def add_expense(self):
        try:
            self.store.add(self.v_date.get().strip(), self.v_cat.get(), self.v_amt.get())
        except ValueError as e:
            messagebox.showerror("Invalid input", f"{e}\n\nUse date format DD-MM-YYYY and a positive numeric amount.")
            return
        self.store.save()
        self.clear_form()
        self.refresh_all("Expense added.")

    def update_expense(self):
        if self.selected is None:
            messagebox.showinfo("Update", "Select an expense from the table first.")
            return
        try:
            self.store.update(self.selected, self.v_date.get().strip(), self.v_cat.get(), self.v_amt.get())
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return
        self.store.save()
        self.clear_form()
        self.refresh_all("Expense updated.")

    def delete_expense(self):
        if self.selected is None:
            messagebox.showinfo("Delete", "Select an expense from the table first.")
            return
        if messagebox.askyesno("Delete", "Delete the selected expense?"):
            self.store.delete(self.selected)
            self.store.save()
            self.clear_form()
            self.refresh_all("Expense deleted.")

    # ---------- Category tab ----------
    def _build_category(self):
        bar = ttk.Frame(self.tab_cat)
        bar.pack(fill="x", padx=10, pady=10)
        ttk.Label(bar, text="Select category:").pack(side="left")
        self.sel_cat = tk.StringVar()
        self.cb_sel_cat = ttk.Combobox(bar, textvariable=self.sel_cat, state="readonly", width=24)
        self.cb_sel_cat.pack(side="left", padx=8)
        self.cb_sel_cat.bind("<<ComboboxSelected>>", lambda e: self.refresh_category())
        self.cat_summary = tk.StringVar()
        ttk.Label(bar, textvariable=self.cat_summary, font=("Segoe UI", 10, "bold"), foreground="#1f4e79").pack(side="left", padx=15)

        body = ttk.Frame(self.tab_cat)
        body.pack(fill="both", expand=True, padx=10)
        frame, self.cat_tree = self._make_tree(body, ("Category", "Total", "Count", "Share"), (180, 120, 70, 70))
        frame.pack(side="left", fill="y")
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.cat_fig, self.cat_canvas = self._make_chart(right, 6, 4)

    def refresh_category(self):
        cats, totals, counts = self.store.category_totals()
        self.cb_sel_cat["values"] = list(cats)
        if cats.size and self.sel_cat.get() not in cats:
            self.sel_cat.set(cats[0])
        self.cat_tree.delete(*self.cat_tree.get_children())
        grand = totals.sum() if totals.size else 0
        for c, t, n in zip(cats, totals, counts):
            self.cat_tree.insert("", "end", values=(c, f"{t:,.2f}", n, f"{t / grand * 100:.1f}%"))
        sel = self.sel_cat.get()
        if sel and cats.size:
            k = int(np.flatnonzero(cats == sel)[0])
            self.cat_summary.set(f"{sel}: {money(totals[k])}  ({counts[k]} expenses, {totals[k] / grand * 100:.1f}% of total)")
        else:
            self.cat_summary.set("")
        self.cat_fig.clear()
        ax = self.cat_fig.add_subplot(111)
        if cats.size:
            colors = ["#c55a11" if c == sel else "#2e75b6" for c in cats]
            ax.barh(cats[::-1], totals[::-1], color=colors[::-1])
        ax.set_title("Total by Category", fontsize=10)
        self.cat_fig.tight_layout()
        self.cat_canvas.draw_idle()

    # ---------- Monthly tab ----------
    def _build_monthly(self):
        bar = ttk.Frame(self.tab_mon)
        bar.pack(fill="x", padx=10, pady=10)
        ttk.Label(bar, text="Select month (MM-YYYY):").pack(side="left")
        self.sel_mon = tk.StringVar()
        self.cb_mon = ttk.Combobox(bar, textvariable=self.sel_mon, state="readonly", width=14)
        self.cb_mon.pack(side="left", padx=8)
        self.cb_mon.bind("<<ComboboxSelected>>", lambda e: self.refresh_monthly())

        self.mon_cards = {}
        row = ttk.Frame(self.tab_mon)
        row.pack(fill="x", padx=10)
        for i, (k, t) in enumerate([("total", "Total"), ("avg", "Average"), ("max", "Highest"),
                                    ("min", "Lowest"), ("count", "Expenses")]):
            box = ttk.LabelFrame(row, text=t, style="Card.TLabelframe")
            box.grid(row=0, column=i, padx=5, sticky="ew")
            row.columnconfigure(i, weight=1)
            v = tk.StringVar(value="-")
            ttk.Label(box, textvariable=v, style="CardValue.TLabel").pack()
            self.mon_cards[k] = v

        body = ttk.Frame(self.tab_mon)
        body.pack(fill="both", expand=True, padx=10, pady=10)
        frame, self.mon_tree = self._make_tree(body, ("Category", "Total", "Count", "Share"), (180, 120, 70, 70))
        frame.pack(side="left", fill="y")
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.mon_fig, self.mon_canvas = self._make_chart(right, 6, 4)

    def refresh_monthly(self):
        months = self.store.months()
        self.cb_mon["values"] = months
        if months and self.sel_mon.get() not in months:
            self.sel_mon.set(months[-1])
        self.mon_tree.delete(*self.mon_tree.get_children())
        self.mon_fig.clear()
        ax = self.mon_fig.add_subplot(111)
        if not months:
            for v in self.mon_cards.values():
                v.set("-")
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            self.mon_canvas.draw_idle()
            return
        mask = self.store.month_mask(self.sel_mon.get())
        st = self.store.stats(mask)
        self.mon_cards["total"].set(money(st["total"]))
        self.mon_cards["avg"].set(money(st["avg"]))
        self.mon_cards["max"].set(money(st["max"]))
        self.mon_cards["min"].set(money(st["min"]))
        self.mon_cards["count"].set(str(st["count"]))
        cats, totals, counts = self.store.category_totals(mask)
        for c, t, n in zip(cats, totals, counts):
            self.mon_tree.insert("", "end", values=(c, f"{t:,.2f}", n, f"{t / st['total'] * 100:.1f}%"))
        # daily spending within the month
        days = np.array([int(d[:2]) for d in np.array(self.store.dates)[mask]])
        daily = np.bincount(days, weights=self.store.amounts[mask], minlength=32)[1:]
        ax.bar(np.arange(1, 32), daily, color="#2e75b6")
        ax.set_title(f"Daily Spending - {self.sel_mon.get()}", fontsize=10)
        ax.set_xlabel("Day of month", fontsize=8)
        self.mon_fig.tight_layout()
        self.mon_canvas.draw_idle()

    # ---------- shared ----------
    def refresh_all(self, msg=None):
        self.cb_cat["values"] = sorted(set(self.store.categories))
        self.refresh_table()
        self.refresh_dashboard()
        self.refresh_category()
        self.refresh_monthly()
        self._status.set(f"{msg + '  ' if msg else ''}{len(self.store)} expenses loaded  |  Data file: {DATA_FILE}")

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if path:
            n = self.store.load(path, replace=False)
            self.store.save()
            self.refresh_all(f"Imported {n} rows.")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if path:
            self.store.save(path)
            messagebox.showinfo("Export", "Expenses exported successfully.")


if __name__ == "__main__":
    App().mainloop()