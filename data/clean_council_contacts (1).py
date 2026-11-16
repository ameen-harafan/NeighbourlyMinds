"""Clean the supplied Victorian council directory; no external data is added.

Usage: python clean_council_contacts.py INPUT.xlsx --output-dir OUTPUT
Dependencies: pandas, openpyxl, matplotlib.
"""
import argparse
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

FIELDS = {
    '2026': 'council_name', 'CEO NAME': 'ceo_name',
    'MAYOR NAME': 'mayor_name', 'Deputy Mayor': 'deputy_mayor_name',
    'TEL': 'telephone', 'EMAIL': 'email', 'WWW SITE': 'website',
    'POSTAL': 'postal_address', 'POSTAL SUBURB': 'postal_suburb',
    'PCODE': 'postcode',
}

def text(value):
    if pd.isna(value):
        return ''
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', str(value))).strip()

def council_id(name):
    """Project ID: stable for the same normalized name, regardless of row order.

    A council rename requires retaining the existing ID in the database or
    maintaining an explicit alias mapping. These are not government LGA codes.
    """
    return str(uuid5(NAMESPACE_URL, 'victorian-council:' + text(name).casefold()))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output-dir', type=Path, default=Path('output'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_excel(args.input, sheet_name='ALL COUNCIL DATA', dtype=object)
    # The year is a heading for the council-name column, not a per-row year.
    raw.columns = [text(c) for c in raw.columns]
    missing = set(FIELDS) - set(raw.columns)
    if missing:
        raise ValueError(f'Missing required source headers: {sorted(missing)}')
    names = raw['2026'].map(text)
    keep = (names.str.contains(r'\bCouncil$|^Borough of Queenscliffe$', regex=True)
            & ~names.str.match(r'(?i)^note\s*:'))
    selected = raw.loc[keep]
    cleaned = selected[list(FIELDS)].rename(columns=FIELDS).copy()
    audit = []

    def log(row, field, original, result, action):
        audit.append({'source_excel_row': int(row) + 2,
                      'council_name': text(raw.loc[row, '2026']),
                      'field': field, 'original_value': text(original),
                      'cleaned_value': result, 'action': action})

    for index in cleaned.index:
        for field in cleaned.columns:
            original = cleaned.at[index, field]
            value = text(original)
            if not pd.isna(original) and str(original) != value:
                log(index, field, original, value, 'trim_or_normalize_whitespace')
            if field == 'postcode' and value:
                value = re.sub(r'\.0$', '', value)
                if not re.fullmatch(r'\d{4}', value):
                    log(index, field, original, value, 'review_invalid_postcode')
            elif field == 'email' and value:
                if value.upper() == 'NO GENERAL EMAIL':
                    value = ''
                    log(index, field, original, value, 'explicit_no_general_email_to_null')
                elif not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
                    log(index, field, original, value, 'review_invalid_email_preserved')
                else:
                    # Domain is case-insensitive; retain local-part case.
                    local, domain = value.rsplit('@', 1)
                    value = local + '@' + domain.lower()
            elif field == 'website' and value:
                if not re.match(r'^https?://', value, flags=re.I):
                    value = 'https://' + value
                    log(index, field, original, value, 'add_https_scheme_not_live_verified')
                if not urlsplit(value).hostname or ' ' in value:
                    log(index, field, original, value, 'review_invalid_website')
            elif field == 'telephone' and value:
                if re.fullmatch(r'\d{4} \d{4}', value):
                    log(index, field, original, value, 'review_area_code_omitted_preserved')
                if re.search(r'[A-Za-z]|/', value):
                    log(index, field, original, value, 'review_vanity_or_multiple_numbers_preserved')
            cleaned.at[index, field] = value
        role = text(raw.at[index, 'MAYOR TITLE'])
        if role and 'mayor' not in role.lower():
            original = cleaned.at[index, 'mayor_name']
            cleaned.at[index, 'mayor_name'] = ''
            log(index, 'mayor_name', original, '',
                f'non_mayor_role_to_null: {role}; original retained in audit')

    duplicate_count = int(cleaned.duplicated().sum())
    cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    keys = cleaned.council_name.str.casefold()
    if keys.duplicated().any():
        raise ValueError('Conflicting duplicate councils; manual resolution required')
    assert cleaned.council_name.ne('').all()
    cleaned.insert(0, 'council_id', cleaned['council_name'].map(council_id))
    if cleaned.council_id.eq('').any() or not cleaned.council_id.is_unique:
        raise ValueError('Council IDs must be nonempty and unique')
    assert list(cleaned.columns) == ['council_id', *FIELDS.values()]
    assert cleaned.postcode.str.fullmatch(r'\d{4}').all()
    assert cleaned.email.eq('').where(cleaned.email.eq(''), cleaned.email.str.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+')).all()
    csv_path = args.output_dir / 'victorian_council_contacts_2026_cleaned.csv'
    cleaned.to_csv(csv_path, index=False, encoding='utf-8-sig')
    audit_path = args.output_dir / 'council_contacts_cleaning_audit.csv'
    pd.DataFrame(audit, columns=['source_excel_row', 'council_name', 'field',
                               'original_value', 'cleaned_value', 'action']).to_csv(
                                   audit_path, index=False, encoding='utf-8-sig')
    reread = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(cleaned, reread)
    draw_erd(args.output_dir)
    blanks = {col: int(cleaned[col].eq('').sum()) for col in cleaned}
    counts = pd.Series([a['action'] for a in audit]).value_counts().to_dict()
    report = f'''# Victorian council contacts — September 2026

Source: supplied {args.input.name}, sheet ALL COUNCIL DATA. No external records were added or checked. Scope is the user's requested field list; an epic specification was not supplied.

## Result

- {len(cleaned)} unique council records; {len(cleaned.columns)} retained fields.
- {len(raw) - len(selected)} non-record rows removed (blank rows, totals and footnotes).
- {duplicate_count} exact duplicate records removed.
- CSV round-trip equality, unique nonempty council IDs, four-digit postcodes and email syntax passed.

## Cleaning decisions

The source heading `2026` maps to `council_name`; its values are names, not years. The file is a September 2026 snapshot. No extra year column is added. A generated council_id column is added as requested.

Whitespace is stripped and repeated whitespace collapsed. Names, titles, apostrophes, postal suburb capitalization and source telephone formats are preserved. Postcodes and telephone numbers are text. Import them as text to preserve leading zeroes.

Website addresses receive an HTTPS scheme for consistent URL structure. This is a formatting choice, not confirmation that HTTPS or the destination works. Email local-part capitalization is preserved; only domains are lowercased.

Port Phillip's explicit NO GENERAL EMAIL marker becomes an empty field. Loddon and Moira have no deputy mayor name supplied. Moira's original MAYOR NAME is Dr Graeme Emonson PSM, but MAYOR TITLE identifies Administrator (Chair), so mayor_name becomes empty rather than misclassifying the administrator. The original entry is retained in the audit.

Eight-digit telephone entries lack area codes; these are flagged, not guessed. Towong and Wodonga explicitly have 02 area codes and retain them. Bass Coast's vanity number and West Wimmera's two numbers remain intact and are flagged. Telephone is therefore a display/contact string, not a universally dial-ready number.

Empty CSV fields represent missing or unavailable values. They do not prove a vacant office. Names, contact ownership, postal validity and current officeholders were not independently verified. Uncertain factual spellings are preserved rather than guessed.

## Schema and ERD

One row represents one council in this snapshot. `council_id` is the primary key (UUID); `council_name` remains a text attribute, unique within this snapshot. IDs are generated with UUID5 from a fixed namespace and normalized council name, so reordering records or adding councils does not change existing IDs. Changes in case or whitespace do not change an ID. A substantive council rename produces a different ID when regenerating from scratch; preserve the existing database ID or maintain an alias mapping for renames. These project IDs are not official government LGA codes. CSV does not enforce database constraints; declare council_id UUID PRIMARY KEY when creating the database table. There are no foreign keys or relationships because all retained fields belong to one council contact entity. The ERD describes the actual CSV; no additional tables are implied. A longitudinal database should store council identity separately from dated contact snapshots.

```mermaid
erDiagram
    COUNCIL_CONTACT {{
        uuid council_id PK
        text council_name
        text ceo_name
        text mayor_name "nullable"
        text deputy_mayor_name "nullable"
        text telephone
        text email "nullable"
        text website
        text postal_address
        text postal_suburb
        char4 postcode
    }}
```

## Missing values

| Field | Empty records |
| --- | ---: |
''' + ''.join(f'| {k} | {v} |\n' for k, v in blanks.items()) + '''
## Audit actions

''' + ''.join(f'- {k}: {v}\n' for k, v in counts.items()) + '''
## Reproduce

Install pandas, openpyxl and matplotlib in your Python environment, then run:

```bash
python clean_council_contacts.py "2026-VIC-COUNCIL-DATA-September-2026.xlsx" --output-dir output
```

The script selects fields by source header, validates data, writes the cleaned CSV and cell-level audit, and generates this report and the ERD. It stops on missing headers or conflicting duplicate council keys. It does not silently replace factual anomalies with invented values.
'''
    (args.output_dir / 'council_contacts_cleaning_report.md').write_text(report, encoding='utf-8')
    print(f'Validated {len(cleaned)} records x {len(cleaned.columns)} fields; missing values: {blanks}')
    print(f'Audit actions: {counts}')

def draw_erd(out):
    fig, ax = plt.subplots(figsize=(9, 9))
    fig.patch.set_facecolor('#f4f7fb')
    ax.set_xlim(0, 10); ax.set_ylim(0, 11); ax.axis('off')
    ax.text(5, 10.5, 'VICTORIAN COUNCIL CONTACTS', ha='center', fontsize=17,
            weight='bold', color='#172d48')
    ax.text(5, 10.05, 'Physical ERD  |  September 2026 snapshot', ha='center', fontsize=11, color='#53667a')
    ax.add_patch(FancyBboxPatch((1, 1.8), 8, 7.7, boxstyle='round,pad=0.02,rounding_size=0.15',
                               facecolor='white', edgecolor='#cad5e2', linewidth=1.5))
    ax.text(1.4, 8.95, 'COUNCIL_CONTACT', fontsize=16, weight='bold', color='#172d48')
    ax.plot([1,9], [8.55,8.55], color='#cad5e2')
    for j, field in enumerate(['council_id', *FIELDS.values()]):
        y = 8.08 - j * .51
        ax.text(1.4, y, 'PK' if j == 0 else '', fontsize=10, weight='bold', color='#087e8b')
        ax.text(2, y, field, fontsize=12, color='#172d48')
        ax.text(8.55, y, 'UUID' if field == 'council_id' else 'CHAR(4)' if field == 'postcode' else 'TEXT',
                ha='right', fontsize=10, color='#53667a')
    ax.text(1.4, 2.15, 'Nullable: mayor_name, deputy_mayor_name, email', fontsize=10, color='#53667a')
    ax.text(5, 1.2, 'One record per council; council_id is the primary key.',
            ha='center', fontsize=10, color='#53667a')
    ax.text(5, .73, 'No foreign keys: the cleaned CSV contains one entity.',
            ha='center', fontsize=10, color='#53667a')
    fig.savefig(out / 'council_contacts_erd.png', dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)

if __name__ == '__main__':
    main()
