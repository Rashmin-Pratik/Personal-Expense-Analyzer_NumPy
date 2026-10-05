# 💰 Personal Expense Analyzer

A desktop application to record, manage and analyse personal expenses, built with **Python**, **NumPy**, **Tkinter** and **Matplotlib**.

It started as a console project and was rebuilt into a full GUI app with charts, data persistence and input validation.

## 📸 Screenshots

**Dashboard**
![Dashboard](screenshots/dashboard.png)

**Expenses**
![Expenses](screenshots/expenses.png)

**Category Analysis**
![Category Analysis](screenshots/category.png)

**Monthly Analysis**
![Monthly Analysis](screenshots/monthly.png)

## ✨ Features

| Tab | What it does |
|-----|--------------|
| **Dashboard** | Total, average, highest, lowest, median, standard deviation, transaction count. Pie chart (spending by category) and bar chart (monthly totals) |
| **Expenses** | Add / update / delete expenses, filter by category text or "amount above", live sum of filtered rows |
| **Category Analysis** | Total, count and percentage share per category with a bar chart |
| **Monthly Analysis** | Pick a month (`MM-YYYY`) to see stats, category breakdown and a daily spending chart |

Extra:
- Auto-save to `expenses.csv` and auto-load on start
- Import / Export CSV from the **File** menu
- Input validation (real `DD-MM-YYYY` dates, positive numeric amounts)
- Case-insensitive categories (`food` = `Food`)

## 🧮 How NumPy is used

All analytics run on NumPy arrays instead of manual loops:

- `np.sum`, `np.mean`, `np.median`, `np.std`, `np.max`, `np.min` for statistics
- `np.argmax` / `np.argmin` to find the highest / lowest expense
- `np.unique(..., return_inverse=True)` + `np.bincount(..., weights=...)` for category totals
- Boolean masks (`amounts > limit`, `month_keys == month`) for filtering
- `np.append`, `np.delete` for array updates

## 🛠 Tech Stack

Python 3.9+ · NumPy · Tkinter (built into Python) · Matplotlib

## 🚀 Getting Started

```bash
# 1. Clone
git clone https://github.com/<your-username>/personal-expense-analyzer.git
cd personal-expense-analyzer

# 2. (Optional) virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python expense_analyzer.py
```

> **Linux:** if Tkinter is missing, run `sudo apt install python3-tk`.

### Try it with demo data
Open the app → **File → Import CSV...** → choose `sample_data/sample_expenses.csv`.

## 📁 Project Structure

```
personal-expense-analyzer/
├── expense_analyzer.py      # ExpenseStore (NumPy data layer) + App (Tkinter GUI)
├── sample_data/
│   └── sample_expenses.csv  # demo data
├── screenshots/             # app screenshots used in this README
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

## 🗺 Roadmap

- [ ] Monthly budget limits with warnings
- [ ] Date-range filter
- [ ] Next-month forecast using `np.polyfit`
- [ ] Export charts as images / PDF report

## 📄 License

Released under the [MIT License](LICENSE).

## 👤 Author

**Your Name** · [GitHub](https://github.com/<your-username>)
