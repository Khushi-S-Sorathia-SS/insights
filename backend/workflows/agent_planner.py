"""
Agent planner for generating Python analysis code.
"""

import os
from typing import Optional

from ..config import get_settings
from ..models.session import DatasetMetadata

settings = get_settings()

# Enable LangSmith tracing if configured
if settings.LANGSMITH_TRACING.lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if settings.LANGSMITH_ENDPOINT:
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    if settings.LANGSMITH_API_KEY:
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    if settings.LANGSMITH_PROJECT:
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT


def _normalize_text(text: str) -> str:
    return text.lower().strip()


def _contains_any(text: str, tokens: list[str]) -> bool:
    return any(token in text for token in tokens)


def generate_analysis_code(user_query: str, dataset: DatasetMetadata) -> str:
    """Generate Python code for data analysis and visualization."""
    query = _normalize_text(user_query)
    columns = [col.lower() for col in dataset.columns]
    csv_filename = dataset.filename

    if "missing" in query:
        return _missing_values_code(csv_filename)

    if "duplicate" in query or "duplicates" in query:
        return _duplicate_rows_code(csv_filename)

    if _contains_any(query, ["salary by department", "department salary", "avg salary by department", "average salary by department"]):
        return _bar_groupby_code(csv_filename, "department", "salary", "Average Salary by Department")

    if _contains_any(query, ["gender vs salary", "salary by gender", "gender salary"]):
        return _bar_groupby_code(csv_filename, "gender", "salary", "Salary by Gender")

    if _contains_any(query, ["experience vs salary", "salary by experience", "experience salary"]):
        return _scatter_code(csv_filename, "experience", "salary", "Experience vs Salary")

    if _contains_any(query, ["department headcount", "headcount by department", "department count"]):
        return _count_by_group_code(csv_filename, "department", "Employee Count by Department")

    if _contains_any(query, ["compare", "vs", "difference"]):
        if "department" in query and "salary" in query:
            return _bar_groupby_code(csv_filename, "department", "salary", "Salary by Department")

    if _contains_any(query, ["plot", "chart", "visual", "graph"]):
        return _generic_plot_code(csv_filename)

    return _summary_code(csv_filename)


def _base_code(dataset_path: str) -> str:
    return f"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

csv_path = r\"{dataset_path}\"
df = pd.read_csv(csv_path)

""".lstrip()


def _missing_values_code(dataset_path: str) -> str:
    return _base_code(dataset_path) + """
missing = df.isna().sum()
missing = missing[missing > 0].sort_values(ascending=False)
if missing.empty:
    print('No missing values found.')
else:
    print('Missing values by column:')
    for col, count in missing.items():
        print(f'{col}: {count}')
    fig, ax = plt.subplots(figsize=(8, 5))
    missing.plot(kind='bar', ax=ax, color='#2563eb')
    ax.set_title('Missing Values by Column')
    ax.set_ylabel('Missing Count')
    plt.tight_layout()
    fig.savefig('analysis_output.png')
"""


def _duplicate_rows_code(dataset_path: str) -> str:
    return _base_code(dataset_path) + """
duplicate_rows = df[df.duplicated(keep=False)]
count = len(duplicate_rows)
print(f'Duplicate row count: {count}')
if count > 0:
    print('Showing up to 5 duplicate rows:')
    print(duplicate_rows.head(5).to_string(index=False))
"""


def _bar_groupby_code(dataset_path: str, group_col: str, value_col: str, title: str) -> str:
    return _base_code(dataset_path) + f"""
df = df.dropna(subset=['{group_col}', '{value_col}'])
if '{group_col}' not in df.columns or '{value_col}' not in df.columns:
    print('Required columns not found in the dataset.')
else:
    grouped = df.groupby('{group_col}', dropna=False)['{value_col}'].mean().sort_values(ascending=False)
    print('Group averages:')
    for key, value in grouped.items():
        print(f'{key}: {value:.2f}')
    fig, ax = plt.subplots(figsize=(8, 5))
    grouped.plot(kind='bar', ax=ax, color='#10b981')
    ax.set_title('{title}')
    ax.set_ylabel('{value_col}')
    ax.set_xlabel('{group_col}')
    plt.tight_layout()
    fig.savefig('analysis_output.png')
"""


def _count_by_group_code(dataset_path: str, group_col: str, title: str) -> str:
    return _base_code(dataset_path) + f"""
df = df.dropna(subset=['{group_col}'])
if '{group_col}' not in df.columns:
    print('Required column not found in the dataset.')
else:
    counts = df['{group_col}'].value_counts().sort_values(ascending=False)
    print('Group counts:')
    for key, value in counts.items():
        print(f'{key}: {value}')
    fig, ax = plt.subplots(figsize=(8, 5))
    counts.plot(kind='bar', ax=ax, color='#6366f1')
    ax.set_title('{title}')
    ax.set_xlabel('{group_col}')
    ax.set_ylabel('Count')
    plt.tight_layout()
    fig.savefig('analysis_output.png')
"""


def _scatter_code(dataset_path: str, x_col: str, y_col: str, title: str) -> str:
    return _base_code(dataset_path) + f"""
df = df.dropna(subset=['{x_col}', '{y_col}'])
if '{x_col}' not in df.columns or '{y_col}' not in df.columns:
    print('Required columns not found in the dataset.')
else:
    print('Scatter plot of {x_col} vs {y_col}')
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(df['{x_col}'], df['{y_col}'], alpha=0.7, c='#ef4444')
    ax.set_title('{title}')
    ax.set_xlabel('{x_col}')
    ax.set_ylabel('{y_col}')
    plt.tight_layout()
    fig.savefig('analysis_output.png')
"""


def _generic_plot_code(dataset_path: str) -> str:
    return _base_code(dataset_path) + """
numeric = df.select_dtypes(include=['number'])
if numeric.empty:
    print('No numeric columns are available for plotting.')
else:
    first_col = numeric.columns[0]
    second_col = numeric.columns[1] if len(numeric.columns) > 1 else first_col
    print(f'Plotting {first_col} vs {second_col}')
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(df[first_col], df[second_col], alpha=0.7, c='#3b82f6')
    ax.set_title(f'{first_col} vs {second_col}')
    ax.set_xlabel(first_col)
    ax.set_ylabel(second_col)
    plt.tight_layout()
    fig.savefig('analysis_output.png')
"""


def _summary_code(dataset_path: str) -> str:
    return _base_code(dataset_path) + """
print('Dataset summary:')
print(df.describe(include='all').to_string())
"""
